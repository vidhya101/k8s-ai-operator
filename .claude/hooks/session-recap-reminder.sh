#!/usr/bin/env bash
# Stop hook: nudge Claude to run /session-recap if the session had meaningful
# activity (edits, mutating commands per audit-log) that would be worth persisting
# to memory MCP before the session ends.
#
# Hook can't invoke MCP tools directly — only Claude can. This just prints a
# reminder that Claude sees on its next turn if the session continues, or that
# the user sees if they scroll back.
set -uo pipefail

audit_log="${CLAUDE_PROJECT_DIR:-.}/.claude/logs/audit.log"

# Only nudge if this session actually logged mutating activity.
if [ ! -f "$audit_log" ]; then
  exit 0
fi

# Rough heuristic: entries from the last hour indicate this session did non-trivial work.
# `date -d` is GNU, not BSD; use a POSIX-safe cutoff via find on the log file's mtime.
if find "$audit_log" -mmin -60 2>/dev/null | grep -q .; then
  printf '\n💡 This session did mutating work (see .claude/logs/audit.log). Consider `/session-recap` to persist findings to memory MCP before ending — the next session will thank you.\n'
fi

exit 0
