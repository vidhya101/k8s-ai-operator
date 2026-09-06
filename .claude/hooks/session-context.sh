#!/usr/bin/env bash
# SessionStart: surface current environment context (git branch, kubectl
# context, terraform workspace, active cloud profile) automatically, so
# .claude/rules/environment-awareness.md doesn't rely purely on remembering
# to check — best-effort, silent about any tool that isn't installed/relevant.
set -uo pipefail

out=""

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch="$(git branch --show-current 2>/dev/null)"
  [ -n "$branch" ] && out="${out}git branch: ${branch}\n"
fi

if command -v kubectl >/dev/null 2>&1; then
  ctx="$(kubectl config current-context 2>/dev/null)"
  [ -n "$ctx" ] && out="${out}kubectl context: ${ctx}\n"
fi

if command -v terraform >/dev/null 2>&1 && [ -d .terraform ]; then
  ws="$(terraform workspace show 2>/dev/null)"
  [ -n "$ws" ] && out="${out}terraform workspace: ${ws}\n"
fi

if [ -n "${AWS_PROFILE:-}" ]; then
  out="${out}AWS profile: ${AWS_PROFILE}\n"
fi

if [ -n "$out" ]; then
  printf 'Environment context detected at session start:\n%b' "$out"
fi

# Nudge Claude to check memory MCP for prior context on this project.
# The recall itself has to be Claude's action (only Claude can call the MCP tools);
# this hook just reminds so the memory-usage rule + /recall-context command actually get used.
project="$(basename "$(pwd)")"
printf '\n💡 Consider `/recall-context %s` to pull prior-session findings for this project (memory MCP).\n' "$project"

exit 0
