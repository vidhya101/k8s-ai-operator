#!/usr/bin/env bash
# Install (or reinstall) the DevOps Hive launchd agents so they run at login.
#
# What this sets up:
#   com.devopshive.memory-sync    — obsidian-sync every 5 min, runs at login
#   com.devopshive.gallery        — the Munder hire gallery server, runs at login
#   com.devopshive.breaker-watcher — cost/rate-limit breaker, ticks every 60 s
#   com.devopshive.headroom-proxy — local compression proxy (127.0.0.1:8787),
#                                   MUST load before munder-difflin — see
#                                   ANTHROPIC_BASE_URL in munder-difflin.plist
#   com.devopshive.munder-difflin — Munder Difflin Electron app, runs at login
#
# Idempotent — safe to re-run any time (unloads first, then re-loads).
#
# Uninstall: pass 'uninstall' as the first argument.
#   .claude/scripts/install-launch-agents.sh uninstall
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC_DIR="${REPO_ROOT}/.claude/launchd"
DEST_DIR="${HOME}/Library/LaunchAgents"
STATE_DIR="${HOME}/.local/state"

AGENTS=(
  com.devopshive.memory-sync.plist
  com.devopshive.gallery.plist
  com.devopshive.breaker-watcher.plist
  com.devopshive.headroom-proxy.plist
  com.devopshive.munder-difflin.plist
)

usage() {
  sed -n '1,15p' "$0" | tail -n +2 | sed 's/^# \?//'
  exit 0
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then usage; fi

if [ "${1:-}" = "uninstall" ]; then
  for plist in "${AGENTS[@]}"; do
    target="${DEST_DIR}/${plist}"
    if [ -f "$target" ]; then
      echo "→ unloading ${plist}"
      launchctl unload "$target" 2>/dev/null || true
      rm -f "$target"
      echo "  removed ${target}"
    fi
  done
  echo "done."
  exit 0
fi

mkdir -p "$DEST_DIR" "$STATE_DIR"

for plist in "${AGENTS[@]}"; do
  src="${SRC_DIR}/${plist}"
  dest="${DEST_DIR}/${plist}"

  if [ ! -f "$src" ]; then
    echo "error: missing source plist ${src}" >&2
    exit 2
  fi

  # If already loaded from a previous install, unload first — launchctl load
  # errors on a duplicate label otherwise.
  if launchctl list 2>/dev/null | awk '{print $3}' | grep -qx "${plist%.plist}"; then
    echo "→ unloading existing ${plist}"
    launchctl unload "$dest" 2>/dev/null || true
  fi

  cp "$src" "$dest"
  chmod 644 "$dest"
  echo "→ loading ${plist}"
  launchctl load "$dest"
done

echo
echo "=== Active DevOps Hive launch agents ==="
launchctl list 2>/dev/null | awk 'NR==1 || /devopshive/'

echo
echo "log files:"
echo "  ${STATE_DIR}/devops-hive-sync.log       # sync run history"
echo "  ${STATE_DIR}/devops-hive-sync.stdout.log"
echo "  ${STATE_DIR}/devops-hive-sync.stderr.log"
echo "  ${STATE_DIR}/devops-hive-gallery.stdout.log"
echo "  ${STATE_DIR}/devops-hive-gallery.stderr.log"
echo
echo "verify gallery is up:"
echo "  curl -s http://127.0.0.1:9977/gallery-index.json | head -3"
echo
echo "manually trigger a sync now:"
echo "  launchctl start com.devopshive.memory-sync"
