#!/usr/bin/env bash
# Verify the multi-provider fallback chain (Claude → Codex → Ollama) is ready
# to use. Reports what's in place and prints the exact command for each gap.
#
# Does NOT install anything by itself. Installing a CLI, starting a service, or
# modifying MCP config all require your review — this script tells you what's
# needed and stays hands-off.
#
# Usage:
#   .claude/scripts/fallback-setup.sh          # verbose report
#   .claude/scripts/fallback-setup.sh --quiet  # exit code only (0 = fully ready)
set -o pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

say() { [ "$QUIET" -eq 0 ] && echo "$@" || true; }
gap=0

say "=============================================================="
say "Fallback provider readiness — Claude → Codex → Ollama chain"
say "=============================================================="

# --- Tier 1: Claude (primary — required) --------------------------------------
say
say "Tier 1 · Claude (primary)"
if command -v claude >/dev/null 2>&1; then
  say "  ✓ claude CLI on PATH ($(claude --version 2>&1 | head -1))"
else
  say "  ✗ claude CLI missing — primary tier cannot function"
  say "    install: see https://claude.com/claude-code"
  gap=$((gap+1))
fi

# --- Tier 2: Codex (mid — optional but recommended) ---------------------------
say
say "Tier 2 · Codex (cloud fallback)"
if command -v codex >/dev/null 2>&1; then
  say "  ✓ codex CLI on PATH ($(codex --version 2>&1 | head -1))"
else
  say "  ✗ codex CLI missing"
  say "    install: npm install -g @openai/codex"
  say "    (verify package name at time of install — OpenAI's CLI package has"
  say "     changed names; also try:  npm search codex openai)"
  gap=$((gap+1))
fi

# OPENAI_API_KEY — check existence only, never print any part of the value.
if [ -n "${OPENAI_API_KEY:-}" ]; then
  say "  ✓ OPENAI_API_KEY is set in current shell (length: ${#OPENAI_API_KEY})"
else
  say "  ✗ OPENAI_API_KEY not in current shell env"
  say "    if it's in ~/.config/devops-tokens.env:"
  say "        source ~/.config/devops-tokens.env"
  say "    if it isn't set at all, create one at https://platform.openai.com/api-keys"
  say "    and add: export OPENAI_API_KEY=sk-..."
  gap=$((gap+1))
fi

# --- Tier 3: Ollama (local — optional, but the whole point of the chain) ------
say
say "Tier 3 · Ollama (local fallback)"
if command -v ollama >/dev/null 2>&1; then
  say "  ✓ ollama CLI installed"
else
  say "  ✗ ollama CLI not installed"
  say "    install: brew install ollama"
  gap=$((gap+1))
fi

# Is the daemon actually running? curl the /api/tags endpoint (safe — returns model list only).
if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
  say "  ✓ ollama service reachable at http://localhost:11434"
  # Count available models (private info, so just the count)
  n=$(curl -s --max-time 2 http://localhost:11434/api/tags \
      | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
  say "    ${n} local model(s) ready"
else
  say "  ✗ ollama service NOT running — start it:"
  say "    brew services start ollama          # keeps it up across reboots"
  say "    # OR"
  say "    ollama serve &                       # one-off, foreground"
  gap=$((gap+1))
fi

# --- Ollama-as-MCP (so Claude agents can CALL Ollama for cheap subtasks) ------
say
say "Ollama-MCP wiring (optional — lets a Claude agent delegate cheap work to Ollama)"
if grep -q "ollama" ~/claude-imp/claude/.mcp.json 2>/dev/null; then
  say "  ✓ ollama MCP already wired in .mcp.json"
else
  say "  ○ ollama MCP not wired — add it with:"
  say "    claude mcp add ollama 'npx -y @rawveg/ollama-mcp' \\"
  say "      -e OLLAMA_HOST=http://localhost:11434"
fi

# --- Codex fallback hires — check they exist -----------------------------------
say
say "Codex fallback hire manifests (12 expected)"
n=$(ls ~/claude-imp/claude/.claude/munder/hires/*-codex.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$n" -eq 12 ]; then
  say "  ✓ ${n}/12 codex fallback hires generated"
else
  say "  ○ ${n}/12 codex fallback hires present — regenerate with:"
  say "    python3 .claude/scripts/generate-fallback-hires.py"
fi

# --- Summary + exit code ------------------------------------------------------
say
say "=============================================================="
if [ "$gap" -eq 0 ]; then
  say "READY — full fallback chain available."
  say "Import the codex hires from the local gallery to spawn peers when needed:"
  say "  open http://127.0.0.1:9977/          # click the -codex rows"
  exit 0
else
  say "$gap gap(s) above — chain will silently skip missing tiers."
  say "You can still work; the missing tiers just aren't there to fall back to."
  exit 1
fi
