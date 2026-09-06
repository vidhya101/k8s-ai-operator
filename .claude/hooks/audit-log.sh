#!/usr/bin/env bash
# PostToolUse: append mutating infra/data commands to a local audit trail.
# Fires only after a command actually ran (i.e. the user already approved it
# via the "ask" gate) — this is a record of what happened, not an extra gate.
set -euo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

mutating='(terraform (apply|destroy|import|state (mv|rm|push))|kubectl (apply|delete|patch|edit|scale|rollout|cordon|uncordon|drain|create)|helm (install|upgrade|uninstall|rollback)|argocd app (create|set|sync|rollback|delete)|docker (push|login)|ansible-playbook|git (push|reset --hard|clean -fd)|gh (pr merge|pr create|workflow run|secret set|release create)|vault (write|delete|kv put|kv delete)|mysql|psql|mongosh|mongo|sqlplus|airflow dags (trigger|pause|unpause|delete)|mlflow (gc|experiments delete|runs delete)|kfp run (submit|delete))'

if printf '%s' "$cmd" | grep -Eiq "$mutating"; then
  log_dir="${CLAUDE_PROJECT_DIR:-.}/.claude/logs"
  mkdir -p "$log_dir"
  printf '%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$cmd" >> "$log_dir/audit.log"
fi

exit 0
