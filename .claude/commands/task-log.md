---
description: Append a line to the current task's who-did-what.md audit log. Use for meaningful decisions or handoffs that the auto-audit hook (which logs bash + write/edit) wouldn't capture.
argument-hint: <who> <what>
allowed-tools: Bash
---

Log a note to who-did-what.md.

!`python3 ~/claude-imp/claude/.claude/scripts/task-scaffold.py log $ARGUMENTS`

Use this for the things the auto-audit hook misses — cross-agent handoffs,
architectural decisions, user redirections, escalations. The auto-hook already
captures every Bash command and every Write/Edit target automatically.
