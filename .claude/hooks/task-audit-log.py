"""Audit-log helper — invoked by task-audit-log.sh with the hook JSON on stdin.

Appends one line per Bash/Write/Edit/NotebookEdit tool call to the current
task's logs/ folder. Fail-open on any error (never blocks the tool call).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def truncate(s: object, limit: int = 800) -> str:
    """One-line, size-capped representation — logs stay grep-friendly even
    when the tool call was a huge Write of a big file."""
    text = str(s or "").replace("\n", " ⏎ ")
    if len(text) <= limit:
        return text
    return text[:limit] + f"… (+{len(text) - limit} more chars)"


def main() -> int:
    # Resolve the current task via symlink; bail silently if none.
    current = Path.home() / "DevOpsHive" / "Tasks" / "current"
    try:
        logs_dir = current.resolve() / "logs"
    except OSError:
        return 0
    if not logs_dir.is_dir():
        return 0

    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool = payload.get("tool_name") or payload.get("toolName") or ""
    inputs = payload.get("tool_input") or payload.get("toolInput") or {}
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if tool == "Bash":
        cmd = inputs.get("command", "")
        line = f"{ts}\t{truncate(cmd)}"
        target = logs_dir / "bash.log"
    elif tool in ("Write", "Edit", "NotebookEdit"):
        fp = inputs.get("file_path") or inputs.get("filePath") or "?"
        line = f"{ts}\t{tool}\t{fp}"
        target = logs_dir / "writes.log"
    else:
        return 0

    try:
        with open(target, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail-open — any unhandled exception is swallowed rather than
        # letting the hook block the underlying tool call.
        sys.exit(0)
