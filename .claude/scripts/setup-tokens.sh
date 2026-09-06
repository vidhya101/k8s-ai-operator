#!/usr/bin/env bash
# setup-tokens.sh — bootstrap the personal ~/.config/devops-tokens.env file.
#
# Copies .claude/config/tokens.env.template → ~/.config/devops-tokens.env,
# sets chmod 600, and adds a `source ...` line to your shell profile if it
# isn't already there. Idempotent — safe to re-run.
#
# Then edit ~/.config/devops-tokens.env, paste your real tokens, and restart
# your shell (or `source ~/.config/devops-tokens.env`) so env vars are set.
#
# NEVER put the personal file back into git. .claude/config/tokens.env.template
# is the ONLY tokens-related file that lives in the repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE="${CLAUDE_ROOT}/config/tokens.env.template"
TARGET="${HOME}/.config/devops-tokens.env"

if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: template not found at $TEMPLATE" >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET")"

if [ -f "$TARGET" ]; then
  echo "Personal tokens file already exists at $TARGET — not overwriting."
  echo "  (if you want to reset it, back up the current file and delete it first, then re-run this script)"
else
  cp "$TEMPLATE" "$TARGET"
  echo "Created $TARGET from template."
fi

# chmod 600: owner read/write only
chmod 600 "$TARGET"
echo "Set permissions to 600 on $TARGET (owner-read-write only)."

# Detect shell profile (zsh on macOS default, bash on Ubuntu default)
PROFILE=""
if [ -n "${ZSH_VERSION:-}" ] || [ "${SHELL##*/}" = "zsh" ]; then
  PROFILE="${HOME}/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [ "${SHELL##*/}" = "bash" ]; then
  # prefer .bashrc on Linux, .bash_profile on macOS
  if [ "$(uname -s)" = "Darwin" ]; then
    PROFILE="${HOME}/.bash_profile"
  else
    PROFILE="${HOME}/.bashrc"
  fi
else
  PROFILE="${HOME}/.profile"
fi

SOURCE_LINE="[ -f ${TARGET} ] && source ${TARGET}"

if [ -f "$PROFILE" ] && grep -qF "$TARGET" "$PROFILE"; then
  echo "Shell profile ($PROFILE) already sources $TARGET — nothing to add."
else
  {
    echo ""
    echo "# Load devops tokens (managed by .claude/scripts/setup-tokens.sh)"
    echo "$SOURCE_LINE"
  } >> "$PROFILE"
  echo "Appended source line to $PROFILE."
fi

cat <<EOF

──────────────────────────────────────────────────────────────────────────────
NEXT STEPS

1. Edit your personal tokens file — put your real values in:

     ${EDITOR:-vim} $TARGET

2. Load it into your current shell (only needed this once; new shells
   pick it up automatically via $PROFILE):

     source $TARGET

3. Verify a few tokens are set (won't print values, just confirms they exist):

     printenv | grep -E '^(ANTHROPIC|OPENAI|GH_TOKEN|AWS_PROFILE)=' | \\
       awk -F= '{print \$1 " is set (length: " length(\$2) ")"}'

The .claude/hooks/block-secret-reads.sh guard already blocks any agent
attempting to \`cat\` / \`grep\` / \`sed\` the tokens file's contents — agents
must read the ENV VAR VALUES, not the file. That's by design.

──────────────────────────────────────────────────────────────────────────────
EOF
