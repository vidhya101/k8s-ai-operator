#!/usr/bin/env bash
# Manual tier-swap helper — one command opens the fallback hire's deep link
# in Munder AND writes a "handoff-context" note into the current task's
# who-did-what.md so the paper trail is clean.
#
# Munder's security posture requires you to click "Spawn" on the modal that
# pops up — this script does everything up to that click.
#
# Usage:
#   .claude/scripts/swap-agent.sh <manager> [reason]
#
# Where <manager> is one of the 12 primary manager names (cloud-manager,
# terraform-manager, etc.) and [reason] is one of the routing-rule reasons:
#   throttled-primary | constrained-by-breaker | cost-optimization | task-class-fit
#
# What it does, in order:
#   1. Confirms the fallback hire manifest exists
#   2. Confirms the local gallery is up on 127.0.0.1:9977
#   3. Fires `open munderdifflin://hire?src=…` to pop Munder's Add-Agent modal
#   4. Logs the swap intent to the current task's who-did-what.md (if a task
#      is active — the /task-start folder — otherwise skips)
#   5. Prints the message-schema stub the newly-spawned peer will need
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <manager> [reason]" >&2
  echo "  manager: cloud-manager | terraform-manager | kubernetes-manager | …" >&2
  echo "  reason:  throttled-primary | constrained-by-breaker | cost-optimization | task-class-fit" >&2
  exit 2
fi

MGR="$1"
REASON="${2:-throttled-primary}"
PORT="${MUNDER_GALLERY_PORT:-9977}"
HIRE="${HOME}/claude-imp/claude/.claude/munder/hires/${MGR}-codex.json"

# 1) Manifest exists?
if [ ! -f "$HIRE" ]; then
  echo "error: no fallback hire for '${MGR}' at ${HIRE}" >&2
  echo "  run: python3 .claude/scripts/generate-fallback-hires.py" >&2
  exit 3
fi

# 2) Gallery reachable?
if ! curl -s --max-time 2 "http://127.0.0.1:${PORT}/gallery-index.json" > /dev/null; then
  echo "error: local gallery not reachable at :${PORT}" >&2
  echo "  ensure com.devopshive.gallery is running (launchctl list | grep gallery)" >&2
  echo "  or start manually: python3 .claude/scripts/serve-munder-hires.py" >&2
  exit 4
fi

# 3) Fire the deep link — Munder catches it and pops the pre-filled Add-Agent modal.
DEEP="munderdifflin://hire?src=http://127.0.0.1:${PORT}/${MGR}-codex.json"
echo "→ opening: ${DEEP}"
open "$DEEP"

# 4) Log the swap into who-did-what.md if a task is active. Non-fatal if no task.
CURRENT="${HOME}/DevOpsHive/Tasks/current"
if [ -L "$CURRENT" ]; then
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  who="${USER}"
  what="tier swap requested — spawn ${MGR}-codex (reason: ${REASON})"
  echo "- \`${ts}\` · **${who}** · ${what}" >> "$(readlink -f "$CURRENT")/who-did-what.md"
  echo "  logged to current task's who-did-what.md"
fi

# 5) Print the handoff message stub. Copy this into the primary agent's terminal
#    so Michael/the manager writes it into the correct outbox.
cat <<EOF

┌─────────────────────────────────────────────────────────────────
│  Once the codex peer is spawned in Munder, the primary agent
│  (${MGR}) should write this handoff into its outbox:
└─────────────────────────────────────────────────────────────────
{
  "kind": "request",
  "from": "${MGR}-<primary-id-from-munder>",
  "to":   "${MGR}-codex-<peer-id-once-spawned>",
  "subject": "Handoff: <describe the work>",
  "body": {
    "reason": "${REASON}",
    "task": "<what needs to be done>",
    "context": ["<file paths the peer needs to read first>"],
    "success_criteria": ["<measurable outcome>"],
    "constraints": { "token_budget": 100000, "deadline": "best-effort" },
    "return_via": "outbox → your-inbox",
    "attribution": "attribute to '${MGR} via ${MGR}-codex' in synthesis"
  },
  "reply_needed": true,
  "hops": 0,
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

Full protocol: .claude/skills/provider-handoff/SKILL.md
EOF
