---
description: End the current task — writes end-time, computes duration, updates the _index.md front matter to status=complete, retires the ~/DevOpsHive/Tasks/current symlink. The task folder itself stays forever as an audit artifact.
argument-hint: [summary]
allowed-tools: Bash
---

Close out the current task.

!`python3 ~/claude-imp/claude/.claude/scripts/task-scaffold.py end $ARGUMENTS`

After this runs, the audit hook stops logging (no `current` symlink means
no logging target). The task folder at `~/DevOpsHive/Tasks/task-<date>-<slug>/`
remains as a permanent audit artifact and continues to show in Obsidian's graph.
