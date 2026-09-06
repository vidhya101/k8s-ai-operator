#!/usr/bin/env bash
# Pull exactly the models the agents reference (from deploy/config.yaml model.* keys), plus the
# embedding model. Talks to the SAME Ollama the operator will use.
set -Eeuo pipefail

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
CFG="${1:-$(dirname "$0")/../deploy/config.yaml}"

echo "Ollama: $OLLAMA_HOST"
curl -fsS "$OLLAMA_HOST/api/tags" >/dev/null || { echo "ERROR: Ollama unreachable at $OLLAMA_HOST"; exit 1; }

# extract the model.* values from the ConfigMap yaml.
# NB: split on the double-quote (awk -F'"' $2) — a naive `sed 's/.*://'` breaks on tags like
# "llama3:8b" (grabs "8b") and BSD sed doesn't support \s. This is portable Linux + macOS.
models="$(grep -E '^[[:space:]]+model\.[A-Za-z]+:' "$CFG" | awk -F'"' 'NF>=2{print $2}' | sort -u)"
[ -n "$models" ] || { echo "ERROR: no model.* keys found in $CFG"; exit 1; }

have="$(curl -fsS "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)"

rc=0
for m in $models; do
  if printf '%s\n' "$have" | grep -qx "$m"; then
    echo "  ✓ $m (present)"
  else
    echo "  ↓ pulling $m  (this can take a while) ..."
    if curl -fsS -N "$OLLAMA_HOST/api/pull" -d "{\"name\":\"$m\"}" \
         | grep -oE '"status":"[^"]*"' | tail -1; then
      echo "    done: $m"
    else
      echo "    !! failed to pull $m — pull it manually:  ollama pull $m"
      rc=1
    fi
  fi
done
echo "installed models now:"
curl -fsS "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/  /'
exit $rc
