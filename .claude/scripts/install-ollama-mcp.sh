#!/usr/bin/env bash
# Safe wrapper around `claude mcp add ollama ...`. Confirms before touching
# ~/.claude.json (or the project .mcp.json depending on scope), verifies
# Ollama is actually reachable before wiring the MCP (adding an MCP that
# points at a dead endpoint would flood every future Claude session with
# connection errors).
#
# Usage:
#   .claude/scripts/install-ollama-mcp.sh          # user scope (~/.claude.json)
#   .claude/scripts/install-ollama-mcp.sh --project # project scope (./.mcp.json)
#   .claude/scripts/install-ollama-mcp.sh --uninstall
set -euo pipefail

SCOPE="user"
UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) SCOPE="project"; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '1,15p' "$0" | tail -n +2 | sed 's/^# \?//'; exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

if ! command -v claude >/dev/null 2>&1; then
  echo "error: claude CLI missing from PATH" >&2
  exit 1
fi

if [ "$UNINSTALL" -eq 1 ]; then
  echo "→ removing ollama MCP..."
  claude mcp remove ollama --scope "$SCOPE" 2>&1 || true
  echo "  done."
  exit 0
fi

# 1) Ollama must be reachable BEFORE wiring the MCP — a dead endpoint would
# generate connection errors on every future session start.
echo "→ checking Ollama endpoint..."
if curl -s --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  count=$(curl -s --max-time 2 http://localhost:11434/api/tags \
    | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null)
  echo "  ✓ Ollama reachable at http://localhost:11434 (${count} model(s))"
else
  echo "  ✗ Ollama not reachable" >&2
  echo "    start it: open -a Ollama  (or: ollama serve &)" >&2
  echo "    then re-run this script" >&2
  exit 1
fi

# 2) Print exact command + get explicit confirmation. Mutating shared config
# without a click is exactly the class of action .claude/rules/safety.md forbids.
CMD=(claude mcp add ollama 'npx -y @rawveg/ollama-mcp' -e OLLAMA_HOST=http://localhost:11434 --scope "$SCOPE")
echo
echo "About to run:"
printf '  %q ' "${CMD[@]}"; echo
echo
echo "Scope: $SCOPE"
echo "  user    → wires into ~/.claude.json (available to every Claude session on this machine)"
echo "  project → wires into ./.mcp.json in the current dir (committed with the repo)"
echo
read -r -p "Proceed? [y/N] " ans
if ! [[ "$ans" =~ ^[Yy]$ ]]; then
  echo "aborted."
  exit 0
fi

echo
echo "→ running claude mcp add..."
"${CMD[@]}"

echo
echo "→ verifying MCP registered..."
if claude mcp list 2>/dev/null | grep -q ollama; then
  echo "  ✓ ollama MCP registered"
  echo
  echo "Restart your Claude Code session to load the new MCP."
  echo "Then any agent can call it — expect tools named 'mcp__ollama__*'."
else
  echo "  ⚠ 'claude mcp list' does not show ollama — check the output above"
  exit 1
fi
