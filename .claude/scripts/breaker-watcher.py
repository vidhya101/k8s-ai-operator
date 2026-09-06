#!/usr/bin/env python3
"""
Breaker-watcher — heuristic daemon that polls Munder's hive for circuit-breaker
events and pings the user via macOS notification when a tier swap is worth
considering.

WHY HEURISTIC. Munder's real breaker state lives on its Electron IPC channel
`control:breakerState`, guarded by a capability token external processes don't
have. Instead we watch the FILE-SYSTEM SIGNAL: agents record breaker messages
into their own memory.md when the harness tells them to STOP or reduce
spending (per Munder's per-agent system prompt). This is lossy — an agent that
gets constrained but doesn't write memory won't trigger — but it's zero-privilege
and works today without forking Munder.

CHECKS PERFORMED EACH TICK (every 60s by default):
  - For each ~/claude-imp/hive/agents/<id>/memory.md:
      - Grep for recent "Circuit breaker" mentions (added since last tick)
      - Detect "constrained" or "stopped" levels in the mention
  - For each mention that's newer than the last check:
      - macOS notification via osascript, suggesting the tier swap
      - Line appended to ~/.local/state/devops-hive-breaker.log

STATE (so we don't re-notify the same event):
  ~/.local/state/devops-hive-breaker-cursor.json
    { "<agent_id>": <last_seen_mtime> }

USAGE
  # one-shot pass (for manual test or cron)
  python3 .claude/scripts/breaker-watcher.py --once

  # daemon mode — polls every 60s until killed
  python3 .claude/scripts/breaker-watcher.py --interval 60

  # under launchd (see .claude/launchd/com.devopshive.breaker-watcher.plist)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
HIVE_AGENTS = HOME / "claude-imp" / "hive" / "agents"
STATE_DIR = HOME / ".local" / "state"
CURSOR_FILE = STATE_DIR / "devops-hive-breaker-cursor.json"
LOG_FILE = STATE_DIR / "devops-hive-breaker.log"

# What we scan for in each agent's memory.md.
# Munder's per-agent system prompt includes literal "Circuit breaker: steer/constrain"
# so when an agent gets told to change behavior, that phrase tends to land in memory.
BREAKER_PATTERNS = [
    re.compile(r"circuit\s*breaker\s*[:\-]?\s*(steer|constrain|stop)", re.IGNORECASE),
    re.compile(r"\b(constrained|stopped)\b.*(budget|tokens|rate.?limit)", re.IGNORECASE),
    re.compile(r"\b(anthropic|api).*(rate.?limit|throttled|429)", re.IGNORECASE),
]


def load_cursor() -> dict[str, float]:
    if not CURSOR_FILE.is_file():
        return {}
    try:
        return json.loads(CURSOR_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_cursor(c: dict[str, float]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CURSOR_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, indent=2))
    tmp.replace(CURSOR_FILE)


def notify(title: str, message: str) -> None:
    """macOS user-facing notification. Falls back to just logging if osascript
    is unavailable (e.g. Linux) — the log itself is the durable record."""
    if not shutil.which("osascript"):
        return
    # Escape double quotes for AppleScript
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            timeout=3,
            capture_output=True,
        )
    except (subprocess.SubprocessError, OSError):
        pass


def log_event(text: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {text}\n")


def guess_manager_name(agent_id: str) -> str:
    """Strip Munder's random suffix. 'cloud-manager-mt42mxfe' → 'cloud-manager'."""
    parts = agent_id.rsplit("-", 1)
    if len(parts) == 2 and 6 <= len(parts[1]) <= 12 and parts[1].isalnum():
        return parts[0]
    return agent_id


def scan_agent(memory_path: Path) -> list[str]:
    """Return any matched breaker-signal lines from the file — one string per hit."""
    if not memory_path.is_file():
        return []
    hits: list[str] = []
    try:
        for line in memory_path.read_text(encoding="utf-8", errors="replace").splitlines():
            for pat in BREAKER_PATTERNS:
                if pat.search(line):
                    hits.append(line.strip()[:200])
                    break
    except OSError:
        return []
    return hits


def tick() -> int:
    """Single sweep. Returns number of new events surfaced."""
    if not HIVE_AGENTS.is_dir():
        return 0

    cursor = load_cursor()
    surfaced = 0

    for agent_dir in sorted(HIVE_AGENTS.iterdir()):
        if not agent_dir.is_dir():
            continue
        mem = agent_dir / "memory.md"
        if not mem.is_file():
            continue

        try:
            mtime = mem.stat().st_mtime
        except OSError:
            continue

        # Only scan if the file changed since last tick.
        last = cursor.get(agent_dir.name, 0.0)
        if mtime <= last:
            continue
        cursor[agent_dir.name] = mtime

        hits = scan_agent(mem)
        if not hits:
            continue

        agent_id = agent_dir.name
        manager = guess_manager_name(agent_id)
        # Preferred swap-target: the codex-fallback peer.
        swap_target = f"{manager}-codex"

        # One notification per agent per tick — bundle if multiple hits.
        msg = f"{manager}: {hits[-1]}"
        notify(
            f"Munder breaker: consider swap → {swap_target}",
            f"{msg[:180]}\nRun: .claude/scripts/swap-agent.sh {manager}",
        )
        log_event(f"agent={agent_id}  suggest={swap_target}  signal={hits[-1]!r}")
        surfaced += 1

    save_cursor(cursor)
    return surfaced


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--once", action="store_true", help="run one tick and exit")
    p.add_argument("--interval", type=int, default=60, help="seconds between ticks (default 60)")
    args = p.parse_args()

    if args.once:
        n = tick()
        print(f"scanned; {n} new event(s) surfaced.")
        return 0

    # Long-running daemon mode — cheap sleep loop with mtime skip.
    print(f"breaker-watcher started; polling every {args.interval}s. ^C to stop.")
    try:
        while True:
            tick()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
