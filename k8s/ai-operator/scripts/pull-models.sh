#!/usr/bin/env bash
# Pull exactly the models the agents reference (from deploy/config.yaml model.* keys), plus the
# embedding model. Talks to the SAME Ollama the operator will use.
set -Eeuo pipefail

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
CFG="${1:-$(dirname "$0")/../deploy/config.yaml}"

echo "Ollama: $OLLAMA_HOST"
curl -fsS "$OLLAMA_HOST/api/tags" >/dev/null || { echo "ERROR: Ollama unreachable at $OLLAMA_HOST"; exit 1; }

# extract the model.* values from the ConfigMap yaml
models="$(grep -E '^\s+model\.[a-zA-Z]+:' "$CFG" | sed -E 's/.*:\s*"?([^"]+)"?\s*$/\1/' | sort -u)"

have="$(curl -fsS "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)"

for m in $models; do
  if printf '%s\n' "$have" | grep -qx "$m"; then
    echo "  ✓ $m (present)"
  else
    echo "  ↓ pulling $m ..."
    curl -fsS "$OLLAMA_HOST/api/pull" -d "{\"name\":\"$m\"}" | tail -c 200; echo
  fi
done
echo "done. Installed models:"
curl -fsS "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/  /'
