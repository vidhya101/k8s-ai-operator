---
description: Start a new task — creates ~/DevOpsHive/Tasks/task-<date>-<slug>/ with readme/flow/tasks/who-did-what/tokens/skills/git/logs/data scaffolding, and points ~/DevOpsHive/Tasks/current at it so the audit hook picks up subsequent tool calls.
argument-hint: <slug> [description]
allowed-tools: Bash
---

Create a new task audit folder for `$ARGUMENTS`.

!`python3 ~/claude-imp/claude/.claude/scripts/task-scaffold.py start $ARGUMENTS`

After this runs, every Bash/Write/Edit tool call from any agent in this session
will be logged automatically to the new task's `logs/` folder via the
`task-audit-log.sh` PostToolUse hook. The `_index.md` at the task root is a
first-class Obsidian note — it appears in the graph immediately.

When the task is done, run `/task-end [summary]` to close it out.
