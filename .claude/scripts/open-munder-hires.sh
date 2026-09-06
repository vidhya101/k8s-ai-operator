#!/usr/bin/env bash
# Open one — or all — Munder-Difflin hire deep links so Munder pops the
# pre-filled Add-Agent modal for each. Requires .claude/scripts/serve-munder-hires.py
# to be running on the same port (default 9977), and Munder-Difflin to be
# installed and registered for the `munderdifflin://` URL scheme.
#
# Usage:
#   .claude/scripts/open-munder-hires.sh                # open all 12, one at a time
#   .claude/scripts/open-munder-hires.sh cloud-manager  # open just one hire
#   .claude/scripts/open-munder-hires.sh --port 9999    # non-default gallery port
#
# WHY THIS EXISTS. Munder's hire flow is deliberately one-import-at-a-time
# (its security posture forbids bulk auto-spawn — see src/shared/hire.ts). We
# can't collapse the 12 Spawn clicks into 1, but we can eliminate every OTHER
# click: no browser visit, no folder-picker per hire, no character-picker.
# You click Spawn 12 times; nothing else.
set -euo pipefail

PORT=9977
ONE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    -h|--help) sed -n '1,15p' "$0" | tail -n +2 | sed 's/^# \?//'; exit 0 ;;
    *) ONE="$1"; shift ;;
  esac
done

HIRE_DIR="$(cd "$(dirname "$0")/../munder/hires" && pwd)"

# Confirm the gallery is up — the deep links won't resolve if serve-munder-hires
# isn't listening. curl-loopback is cheap; fail fast with a clear message.
if ! curl -s --max-time 2 "http://127.0.0.1:${PORT}/gallery-index.json" > /dev/null; then
  echo "error: gallery not reachable at http://127.0.0.1:${PORT}/" >&2
  echo "  start it first: python3 .claude/scripts/serve-munder-hires.py --port ${PORT}" >&2
  exit 1
fi

# Managers, in the recommended cost-conscious spawn order. Michael (orchestrator)
# is auto-provisioned by Munder — we do not open a hire for him.
MANAGERS=(
  cloud-manager
  terraform-manager
  kubernetes-manager
  observability-manager
  sre-manager
  cicd-manager
  docker-manager
  github-manager
  linux-manager
  ansible-manager
  aiops-manager
  mlops-manager
)

open_one() {
  local m="$1"
  local link="munderdifflin://hire?src=http://127.0.0.1:${PORT}/${m}.json"
  local file="${HIRE_DIR}/${m}.json"
  if [ ! -f "$file" ]; then
    echo "error: no manifest for '${m}' at ${file}" >&2
    echo "  run: python3 .claude/scripts/generate-munder-hires.py" >&2
    return 2
  fi
  echo "→ opening ${m}"
  open "$link"
}

if [ -n "$ONE" ]; then
  open_one "$ONE"
  exit $?
fi

echo "Opening all 12 hires — Munder will pop one Add-Agent modal per hire."
echo "For each: verify the workspace = your repo dir (containing .claude/),"
echo "then click Spawn. Press ctrl-c to stop between hires."
echo
for m in "${MANAGERS[@]}"; do
  open_one "$m"
  # 4-sec gap so you can review-and-spawn each modal before the next fires;
  # Munder's modal is single-instance, so a new deep link replaces the previous
  # one if you haven't hit Spawn yet.
  sleep 4
done
echo
echo "Done. All 12 hires opened."
