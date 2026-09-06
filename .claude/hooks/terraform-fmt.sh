#!/usr/bin/env bash
# PostToolUse: auto-format a .tf file after Claude edits it, so formatting
# never becomes something to review/nitpick.
set -euo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

if [ -n "$file" ] && [ "${file##*.}" = "tf" ] && command -v terraform >/dev/null 2>&1; then
  terraform -chdir="$(dirname "$file")" fmt >/dev/null 2>&1 || true
fi

exit 0
