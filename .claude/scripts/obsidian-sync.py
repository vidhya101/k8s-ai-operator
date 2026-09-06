#!/usr/bin/env python3
"""
Sync all the team's memory into an Obsidian vault so you (and the agents
themselves) can pull prior context WITHOUT re-deriving it, saving tokens on
every subsequent task.

WHAT GETS SYNCED
  Sources:                                             → Vault destination:
  ─────────────────────────────────────────────────────────────────────────────
  ~/claude-imp/hive/agents/*/memory.md                  DevOpsHive/HiveMemory/<agent>.md
  ~/claude-imp/hive/agents/*/inbox/*.json  (unread)     DevOpsHive/HiveMemory/<agent>.md  (linked)
  ~/.claude/projects/*/memory/*.md                      DevOpsHive/CrossSession/*.md
  ~/claude-imp/claude/.claude/agents/*.md               DevOpsHive/Team/<agent>.md         (static roster)
  Auto-generated:                                        DevOpsHive/README.md               (index)

WHY IT PROTECTS TOKENS
  Before an agent burns tokens re-deriving context, it can Read
  DevOpsHive/HiveMemory/<its-name>.md — which contains its actual working memory
  as it accumulated across previous tasks, plus [[wikilinks]] to other agents
  it collaborated with. Obsidian renders these as a graph so a human can
  navigate, and agents can grep the same files as plain markdown.

DESIGN NOTES
  - IDEMPOTENT: safe to run every N minutes via launchd. Skips writes when the
    source file hash hasn't changed (checked via mtime + size).
  - NO SECRET LEAKAGE: reads only memory/roster files; never touches config
    files, .env, tfstate, or the integration-secrets store.
  - LINKED, NOT COPIED: agent identity is preserved via [[wikilinks]] so
    Obsidian's graph view shows real relationships when a manager writes about
    delegating to a sub-agent.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HOME = Path.home()

# Dedicated vault outside ~/Documents. Documents is TCC-protected on macOS
# Sonoma+, and launchd background jobs are denied read/write access to it
# unless the user grants Full Disk Access to python3 via System Settings.
# Using ~/DevOpsHive dodges that entirely — no permission dialogs, no re-approval
# after each macOS update. The user opens this in Obsidian as a NEW vault via
# File → Open Vault → Open folder as vault → pick ~/DevOpsHive.
#
# If you prefer this to live under ~/Documents/Obsidian Vault/DevOpsHive/ instead,
# grant Full Disk Access to /usr/bin/python3 in System Settings → Privacy &
# Security → Full Disk Access, then change VAULT_ROOT below.
VAULT_ROOT = HOME / "DevOpsHive"
DEVOPS_HIVE = VAULT_ROOT

# Sources
HIVE_AGENTS_DIR = HOME / "claude-imp" / "hive" / "agents"
TEAM_AGENTS_DIR = HOME / "claude-imp" / "claude" / ".claude" / "agents"
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
# Live IDE state — written by the DevOps Hive VS Code extension when installed
# (see .claude/vscode/extension/). Absent if the extension isn't running; sync
# treats absence as a no-op.
VSCODE_CTX_SRC = HOME / "DevOpsHive" / "state" / "vscode-context.md"

# Dest layout
DIR_HIVE_MEM = DEVOPS_HIVE / "HiveMemory"
DIR_TEAM = DEVOPS_HIVE / "Team"
DIR_CROSS = DEVOPS_HIVE / "CrossSession"
DIR_TASKS = DEVOPS_HIVE / "Tasks"
DIR_LIVE = DEVOPS_HIVE / "Live"

# Log file for diagnostics — used by the launchd job to prove the last run.
LOG = HOME / ".local" / "state" / "devops-hive-sync.log"

# One-line "manager owns which characters + domain tags" cheat table so the
# vault reader (human or agent) can find the right note quickly.
MANAGER_CHARACTERS = {
    "orchestrator":         ("michael",  "GOD, routing"),
    "cloud-manager":        ("jim",      "aws · azure · gcp · landing-zone · iam · cost"),
    "observability-manager":("pam",      "prometheus · grafana · loki · datadog · otel"),
    "sre-manager":          ("dwight",   "slo · error-budget · oncall · incident · chaos"),
    "cicd-manager":         ("oscar",    "pipeline · gates · promotion · artifacts"),
    "terraform-manager":    ("angela",   "modules · state · plan-review · checkov"),
    "linux-manager":        ("stanley",  "systemd · sysctl · kernel · packages"),
    "docker-manager":       ("kevin",    "dockerfile · hardening · scans · sbom"),
    "github-manager":       ("andy",     "repos · branch-protection · actions · dependabot"),
    "ansible-manager":      ("phyllis",  "playbooks · idempotency · vault · inventory"),
    "aiops-manager":        ("kelly",    "anomaly · alert-noise · auto-remediation"),
    "mlops-manager":        ("ryan",     "training · registry · serving · drift"),
    "kubernetes-manager":   ("creed",    "k8s · eks · aks · gke · openshift · helm · argo"),
}

WIKILINK_RE = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b")  # kebab-case agent names


def ensure_dirs() -> None:
    for d in (DEVOPS_HIVE, DIR_HIVE_MEM, DIR_TEAM, DIR_CROSS, DIR_TASKS, DIR_LIVE, LOG.parent):
        d.mkdir(parents=True, exist_ok=True)


def content_hash(text: str) -> str:
    """Content-addressed marker so we skip re-writes when nothing changed."""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


def write_if_changed(dest: Path, text: str, log: list[str]) -> bool:
    """Idempotent write — skips if content is unchanged (byte-identical),
    preventing needless Obsidian re-indexes and file-watcher spam."""
    if dest.exists() and dest.read_text(encoding="utf-8", errors="replace") == text:
        return False
    dest.write_text(text, encoding="utf-8")
    log.append(f"wrote  {dest.relative_to(DEVOPS_HIVE)}")
    return True


def sprinkle_wikilinks(body: str, known: set[str]) -> str:
    """Turn any kebab-case agent name in the body into an Obsidian [[wikilink]]
    the FIRST time it appears per file. Non-destructive — leaves the original
    text intact when the token isn't a known agent."""
    if not body:
        return body
    seen: set[str] = set()

    def _rep(m: re.Match) -> str:
        tok = m.group(1)
        if tok in known and tok not in seen:
            seen.add(tok)
            return f"[[{tok}]]"
        return tok

    return WIKILINK_RE.sub(_rep, body)


def render_hive_memory(agent_id: str, agent_dir: Path, known: set[str]) -> str:
    """Compose one Obsidian note from a hive agent's memory + inbox + outbox
    counts. Front-matter carries the metadata Obsidian's dataview + graph use."""
    memory_path = agent_dir / "memory.md"
    memory = memory_path.read_text(encoding="utf-8", errors="replace") if memory_path.is_file() else ""

    # Split agent id -> display name (strip Munder's random suffix).
    display = agent_id.rsplit("-", 1)[0] if "-" in agent_id and len(agent_id.rsplit("-", 1)[-1]) <= 10 else agent_id
    character, tags = MANAGER_CHARACTERS.get(display, ("", ""))

    inbox_dir = agent_dir / "inbox"
    inbox_pending = len([p for p in inbox_dir.glob("*.json")]) if inbox_dir.is_dir() else 0
    inbox_done = len([p for p in (inbox_dir / ".done").glob("*.json")]) if (inbox_dir / ".done").is_dir() else 0

    outbox_dir = agent_dir / "outbox"
    outbox_pending = len(list(outbox_dir.glob("*.json"))) if outbox_dir.is_dir() else 0

    body = sprinkle_wikilinks(memory, known)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    fm = [
        "---",
        f"type: hive-memory",
        f"agent: {display}",
        f"agent_id: {agent_id}",
        f"character: {character}",
        f"tags: [{tags}]" if tags else "tags: []",
        f"inbox_pending: {inbox_pending}",
        f"inbox_done: {inbox_done}",
        f"outbox_pending: {outbox_pending}",
        f"last_synced: {now}",
        "---",
        "",
        f"# {display}",
        "",
        f"Live working memory for `{agent_id}` inside the Munder hive.",
        f"Character: **{character or '—'}**. See [[{display}]] for the static role definition.",
        "",
        f"- Inbox pending: **{inbox_pending}** · done: {inbox_done}",
        f"- Outbox pending: **{outbox_pending}**",
        f"- Last synced: `{now}`",
        "",
        "## Memory",
        "",
        body if body.strip() else "*(no memory recorded yet — this agent hasn't handled a task)*",
        "",
    ]
    return "\n".join(fm)


def render_team_role(agent_file: Path, known: set[str]) -> str:
    """Static role card, from the agent's frontmatter + full instruction body.
    This is the reference the manager reads before delegating."""
    text = agent_file.read_text(encoding="utf-8", errors="replace")
    name = agent_file.stem
    character, tags = MANAGER_CHARACTERS.get(name, ("", ""))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    body = sprinkle_wikilinks(text, known)

    return "\n".join([
        "---",
        f"type: agent-role",
        f"agent: {name}",
        f"character: {character}",
        f"tags: [{tags}]" if tags else "tags: []",
        f"source: {agent_file.relative_to(HOME)}",
        f"last_synced: {now}",
        "---",
        "",
        f"# {name}",
        "",
        f"Static role definition. Live memory is at [[HiveMemory/{name}]] once the agent has started working.",
        "",
        "---",
        "",
        body,
        "",
    ])


def render_cross_session(source: Path) -> str:
    """Pass a `~/.claude/projects/*/memory/*.md` file through unchanged (it's
    already the right shape — YAML front matter + body + [[wikilinks]])."""
    return source.read_text(encoding="utf-8", errors="replace")


def render_index(hive_agents: list[str], team_agents: list[str], recent_tasks: list[Path]) -> str:
    """DevOpsHive/README.md — the entry point Obsidian opens by default. Shows
    a token-cheap "who's on the floor + what happened lately" summary agents
    can pull with one Read call to skip re-derivation."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "---",
        "type: index",
        f"last_synced: {now}",
        "---",
        "",
        "# DevOps Hive — memory graph",
        "",
        "**Purpose:** protect tokens. Before an agent re-derives context, it Reads",
        "the note at `HiveMemory/<its-own-name>.md` — carries its accumulated memory,",
        "inbox counts, and [[wikilinks]] to the peers it's collaborated with.",
        "",
        "**Human view:** open Obsidian → toggle Graph View (⌘⌥G) → filter path:DevOpsHive/",
        "for the full team topology.",
        "",
        "## Live agents on the floor",
        "",
        "| Agent | Character | Domain tags | Current memory |",
        "| ----- | --------- | ----------- | -------------- |",
    ]
    for agent_id in sorted(hive_agents):
        display = agent_id.rsplit("-", 1)[0]
        character, tags = MANAGER_CHARACTERS.get(display, ("", ""))
        lines.append(f"| `{display}` | {character} | {tags} | [[HiveMemory/{agent_id}]] |")

    lines += [
        "",
        "## Static roster (role definitions)",
        "",
    ]
    for name in sorted(team_agents):
        lines.append(f"- [[Team/{name}]]")

    lines += [
        "",
        "## Recent task notes",
        "",
    ]
    if recent_tasks:
        for t in recent_tasks[:20]:
            # Each task's _index.md lives at Tasks/task-.../_index.md — the
            # note title in Obsidian is the parent-dir name.
            task_dir_name = t.parent.name
            lines.append(f"- [[Tasks/{task_dir_name}/_index|{task_dir_name}]]")
    else:
        lines.append("*(no task notes yet — run `/task-start <slug>` to kick one off)*")

    lines += [
        "",
        "---",
        "",
        f"_Auto-synced by `.claude/scripts/obsidian-sync.py` — last run `{now}`._",
        "",
    ]
    return "\n".join(lines)


def known_agent_names(team_dir: Path) -> set[str]:
    """The set of kebab-case names sprinkle_wikilinks() may link to."""
    return {p.stem for p in team_dir.glob("*.md")}


def main() -> int:
    # Bootstrap the vault on first run — this is a dedicated Obsidian vault we
    # create if missing. The user opens it in Obsidian via File → Open Vault.
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    ensure_dirs()
    log: list[str] = []
    known = known_agent_names(TEAM_AGENTS_DIR) if TEAM_AGENTS_DIR.is_dir() else set()

    # 1) Hive memory — one note per running agent.
    hive_agent_ids: list[str] = []
    if HIVE_AGENTS_DIR.is_dir():
        for agent_dir in sorted(HIVE_AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir():
                continue
            hive_agent_ids.append(agent_dir.name)
            body = render_hive_memory(agent_dir.name, agent_dir, known)
            write_if_changed(DIR_HIVE_MEM / f"{agent_dir.name}.md", body, log)

    # 2) Static team roster — one note per .claude/agents/*.md role file.
    team_names: list[str] = []
    if TEAM_AGENTS_DIR.is_dir():
        for agent_file in sorted(TEAM_AGENTS_DIR.glob("*.md")):
            if agent_file.name == "TEAM_ROSTER.md":
                continue
            team_names.append(agent_file.stem)
            body = render_team_role(agent_file, known)
            write_if_changed(DIR_TEAM / agent_file.name, body, log)

    # 3) Cross-session memory — carry .claude/memory/*.md across.
    if CLAUDE_PROJECTS.is_dir():
        for mem_file in CLAUDE_PROJECTS.glob("*/memory/*.md"):
            if mem_file.name == "MEMORY.md":
                # Copy the index too so Obsidian's graph can traverse it.
                write_if_changed(DIR_CROSS / "MEMORY.md",
                                 render_cross_session(mem_file), log)
                continue
            write_if_changed(DIR_CROSS / mem_file.name,
                             render_cross_session(mem_file), log)

    # 3b) Live VS Code context — copy the extension's output into the vault
    # so it shows in the graph. Absent = extension not running; skip silently.
    if VSCODE_CTX_SRC.is_file():
        try:
            src_text = VSCODE_CTX_SRC.read_text(encoding="utf-8", errors="replace")
            write_if_changed(DIR_LIVE / "vscode-context.md", src_text, log)
        except OSError:
            pass

    # 4) Rebuild index using discovered inventory. Tasks live as folders
    # (task-YYYY-MM-DD-<slug>/) with an _index.md inside — sort those by their
    # start-time.txt content so the most recent tasks bubble to the top of
    # the vault's README index.
    recent_tasks = sorted(
        DIR_TASKS.glob("task-*/_index.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    write_if_changed(DEVOPS_HIVE / "README.md",
                     render_index(hive_agent_ids, team_names, recent_tasks), log)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] synced {len(log)} file(s); {len(hive_agent_ids)} hive agents, {len(team_names)} roles\n")
        for line in log[:50]:
            f.write(f"  {line}\n")

    print(f"synced {len(log)} file(s) into {DEVOPS_HIVE}")
    for line in log[:20]:
        print(f"  {line}")
    if len(log) > 20:
        print(f"  … and {len(log)-20} more (see {LOG})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
