#!/usr/bin/env bash
# Install (or uninstall) the DevOps Hive VS Code Context extension locally.
#
# We don't publish to the marketplace — this is your own tiny extension. Install
# is: copy the extension folder into ~/.vscode/extensions/<publisher>.<name>-<ver>/
# and restart VS Code. Zero external deps to fetch (extension uses only the vscode
# API + Node built-ins), so no `npm install` step.
#
# Usage:
#   .claude/vscode/extension/install.sh            # install
#   .claude/vscode/extension/install.sh uninstall  # remove
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
PUBLISHER=$(python3 -c "import json; print(json.load(open('$SRC/package.json'))['publisher'])")
NAME=$(python3 -c "import json; print(json.load(open('$SRC/package.json'))['name'])")
VERSION=$(python3 -c "import json; print(json.load(open('$SRC/package.json'))['version'])")
DEST="$HOME/.vscode/extensions/${PUBLISHER}.${NAME}-${VERSION}"

if [ "${1:-}" = "uninstall" ]; then
  if [ -d "$DEST" ]; then
    echo "→ removing $DEST"
    rm -rf "$DEST"
    echo "  done. Restart VS Code (or run 'Developer: Reload Window')."
  else
    echo "  not installed at $DEST — nothing to do."
  fi
  exit 0
fi

if ! command -v code >/dev/null 2>&1; then
  echo "error: VS Code 'code' CLI not on PATH." >&2
  echo "       enable it: VS Code → ⌘⇧P → 'Shell Command: Install code command in PATH'" >&2
  exit 1
fi

echo "→ installing ${PUBLISHER}.${NAME} v${VERSION} to ${DEST}"
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$SRC/package.json" "$SRC/extension.js" "$SRC/README.md" "$DEST/"

echo "  ✓ copied"
echo
echo "Next steps:"
echo "  1. Restart VS Code   (or ⌘⇧P → 'Developer: Reload Window')"
echo "  2. Verify install:   code --list-extensions | grep ${NAME}"
echo "  3. Trigger a manual publish once VS Code is loaded:"
echo "         ⌘⇧P → 'DevOps Hive: Publish Context Now'"
echo "  4. Confirm the context file exists:"
echo "         cat ~/DevOpsHive/state/vscode-context.md | head"
