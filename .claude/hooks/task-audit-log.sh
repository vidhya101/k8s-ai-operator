#!/usr/bin/env bash
# PostToolUse hook — thin wrapper that hands the JSON payload to the Python
# audit helper. Kept minimal so the bash side has no chance of hanging on
# stdin (an earlier version used a heredoc + herestring combo that competed
# for stdin and silently swallowed the payload).
#
# FAIL-OPEN. Any error MUST NOT block the tool call. Every failure path
# silently exits 0; the tool call proceeds regardless.
set +e

CURRENT="$HOME/DevOpsHive/Tasks/current"
[ -L "$CURRENT" ] || exit 0

exec python3 "$(dirname "$0")/task-audit-log.py" 2>/dev/null
exit 0
