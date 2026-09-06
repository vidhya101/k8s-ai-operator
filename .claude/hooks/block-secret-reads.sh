#!/usr/bin/env bash
# PreToolUse guard for Bash calls — content-inspects the command to block
# obvious secret-file reads that the Read-tool deny list can't see (Bash
# `cat .env`, `grep SECRET .env`, `awk … credentials`, etc.).
#
# TIGHTENED (2026-08) after real-world friction — the earlier version fired
# on every command that MENTIONED a sensitive path (e.g. checking existence
# with `awk`, iterating with `python`, structural JSON reads), even when
# nothing sensitive was actually printed. The current design has three tiers:
#
#   1. HARD BLOCK          — a shell content-command (cat/head/tail/less/…)
#                           paired with a sensitive filename pattern IN AN
#                           ARGUMENT POSITION (not just anywhere in the line).
#                           Always denied.
#
#   2. SCRIPT INTERPRETERS — python/node/ruby/perl only blocked when the
#                           command clearly performs a file-read call
#                           (open("X"), Path("X").read_text(), require('fs'),
#                           fs.readFileSync, File.read, etc.) AND the target
#                           path matches the sensitive pattern. Bare mentions
#                           of a filename in a variable no longer trigger.
#
#   3. SAFE UTILITIES      — wc, grep -c/-l, stat, test, [, ls, file, find,
#                           du, cmp -s — these don't reveal contents, always
#                           allowed even if they touch sensitive paths.
#
#   4. NULL SINKS          — if the command's stdout goes to /dev/null or
#                           is piped into wc/grep -c/-l, whatever content
#                           was read isn't visible → allow.
#
# Still a heuristic; still complementary to the Read-tool deny list; still
# fail-closed on ambiguity.
set -euo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

# ── Tier 4 (NULL SINKS): if the whole command's output is dropped, allow. ──
# Match: `… > /dev/null`, `… 2>&1 > /dev/null`, or `… | wc -l|-c`, or
# `… | grep -c/-l/--files-with-matches …`. Anything pipe-ending in a
# size/count-only sink is safe by construction.
if printf '%s' "$cmd" | grep -Eq '>\s*/dev/null\s*(2>&1)?\s*$'; then
  exit 0
fi
if printf '%s' "$cmd" | grep -Eq '\|\s*(wc(\s+-[clm]+)?|grep\s+(-[clL]+|--files-with-matches)|awk\s+.END\{print\s+NR\}.)\s*(\||$)'; then
  exit 0
fi

# ── Tier 3 (SAFE UTILITIES): explicit allow-list even when they touch
# sensitive paths. Existence checks, size probes, list-only ops. Never leak
# content by design. ──
safe_only_head='^\s*(wc|stat|test|\[|file|du|find|ls|cmp\s+-s|jq\s+-e\s+empty|shasum|sha256sum|md5|md5sum|openssl\s+dgst)([[:space:]]|$)'
if printf '%s' "$cmd" | grep -Eq "$safe_only_head"; then
  exit 0
fi

# ── Sensitive filename patterns — use \b (word boundary) throughout so we
# correctly match `.env`, `foo.env`, `secrets.env`, `.env.production` at
# end-of-string / before quote-and-backslash / before punctuation, WITHOUT
# false-matching `.envrc`, `.env.template`, `env-config.json`.
# `.env.<suffix>` is a separate alternative so we still catch `.env.production`.
sensitive_pattern='(\.env(\.[A-Za-z0-9_-]+)?\b|\.pem\b|\.key\b|\bid_rsa\b|\bid_ed25519\b|\bid_ecdsa\b|\bid_dsa\b|\.pgpass\b|\.my\.cnf\b|\.netrc\b|\.tfstate(\.[A-Za-z0-9_-]+)?\b|\bkubeconfig\b|\.kube/config\b|\.p12\b|\.pfx\b|\bcwallet\.sso\b|\bewallet\.p12\b|(aws|azure|gcp|oci)/credentials\b|\bdevops-tokens\.env\b|\bintegration-secrets\.json\b)'

# ── Tier 1 (HARD BLOCK): shell content commands ──
# These commands EXIST to print file contents; if the sensitive pattern appears
# as an argument, block. We separate them from script interpreters (below) so
# the interpreter check can be gentler.
shell_content_cmd='(^|[|&;]|[[:space:]])(cat|head|tail|less|more|bat|strings|xxd|od|base64|source|\.\s+)([[:space:]]|$)'

if printf '%s' "$cmd" | grep -Eiq "$shell_content_cmd" \
  && printf '%s' "$cmd" | grep -Eiq "$sensitive_pattern"; then
  echo "secret-guard: shell content-command paired with a sensitive-file pattern:" >&2
  echo "  $cmd" >&2
  echo "Blocked. If this is genuinely needed, ask the user directly rather than reading it into context (see .claude/rules/secrets.md)." >&2
  exit 2
fi

# ── Tier 1b: content-revealing utilities on sensitive files ──
# grep / awk / sed / rg with a file argument that's sensitive → block, UNLESS
# they're in count/list-only mode (already handled by tier 4 pipe check + we
# add explicit flag checks here too).
grep_awk_cmd='(^|[|&;]|[[:space:]])(grep|egrep|fgrep|rg|awk|sed|perl\s+-p|perl\s+-n|ruby\s+-p|ruby\s+-n)([[:space:]]|$)'
if printf '%s' "$cmd" | grep -Eiq "$grep_awk_cmd" \
  && printf '%s' "$cmd" | grep -Eiq "$sensitive_pattern"; then
  # Allow count/list-only forms — these don't emit content.
  if printf '%s' "$cmd" | grep -Eq '\bgrep\s+[^|]*-[a-zA-Z]*[cLl][a-zA-Z]*\b'; then
    exit 0
  fi
  echo "secret-guard: text-processing utility paired with a sensitive-file pattern:" >&2
  echo "  $cmd" >&2
  echo "If you only need to check existence/count, add -c or -l for grep, or pipe to wc/awk 'END{print NR}'." >&2
  exit 2
fi

# ── Tier 2 (SCRIPT INTERPRETERS): stricter check — must be an actual
# file-read call, not just a mention. This lets legitimate Python one-liners
# that reference `.env` in a variable name or path composition proceed. ──
interpreter_cmd='(^|[|&;]|[[:space:]])(python[0-9.]*|node|ruby|perl|mysql|psql|mongosh|mongo|sqlplus|vault)([[:space:]]|$)'
# A "reading" call = anything that emits bytes from a file to stdout / into a
# structure the process could then print. Distinct from `os.path.exists`,
# `Path("...").is_file()`, `stat`, `getsize` — those are metadata only.
reading_call_pattern='(open\s*\(|read_text\s*\(|read_bytes\s*\(|readlines\s*\(|\.read\s*\(|readFileSync|readFile\s*\(|require\s*\(|File\.read|IO\.read|slurp|Load\s*\(|-r\s*<\s*|<\s*\$|<\s*['\''"]|include\s*['\''"])'

if printf '%s' "$cmd" | grep -Eiq "$interpreter_cmd" \
  && printf '%s' "$cmd" | grep -Eiq "$sensitive_pattern" \
  && printf '%s' "$cmd" | grep -Eq "$reading_call_pattern"; then
  echo "secret-guard: script interpreter appears to read a sensitive file:" >&2
  echo "  $cmd" >&2
  echo "If you're only checking existence / structure without printing the contents, use os.path.exists / Path.is_file / stat instead." >&2
  exit 2
fi

# ── Tier 1c: database CLIs pointed at a sensitive-looking file (mysql < X.env, etc.) ──
db_cli='(^|[|&;]|[[:space:]])(mysql|psql|mongosh|sqlplus|vault)([[:space:]]|$)'
if printf '%s' "$cmd" | grep -Eiq "$db_cli" \
  && printf '%s' "$cmd" | grep -Eq '<\s*\S*'"$sensitive_pattern"; then
  echo "secret-guard: database CLI reading from a sensitive-file redirect:" >&2
  echo "  $cmd" >&2
  exit 2
fi

exit 0
