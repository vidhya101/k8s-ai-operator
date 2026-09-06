#!/usr/bin/env bash
# Validates every SKILL.md against this repo's established conventions.
# Encodes the ad hoc checks used throughout this setup's construction into
# one reusable, dependency-free script (bash + grep only — no PyYAML/pip
# install required, unlike a Python-based validator).
#
# Usage: .claude/scripts/validate-skills.sh
# Exit code is non-zero if any check fails.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILLS_DIR="$ROOT/.claude/skills"
fail=0

echo "Validating skills in $SKILLS_DIR ..."
echo

# 1. Every skill dir has a SKILL.md with valid, non-broken frontmatter.
for dir in "$SKILLS_DIR"/*/; do
  name="$(basename "$dir")"
  f="$dir/SKILL.md"
  if [ ! -f "$f" ]; then
    echo "FAIL  $name: no SKILL.md"; fail=1; continue
  fi

  first_line="$(head -1 "$f")"
  if [ "$first_line" != "---" ]; then
    echo "FAIL  $name: frontmatter doesn't start with ---"; fail=1
  fi

  name_count=$(head -6 "$f" | grep -c "^name:")
  desc_count=$(head -6 "$f" | grep -c "^description:")
  [ "$name_count" -ne 1 ] && { echo "FAIL  $name: expected exactly one 'name:' line, found $name_count"; fail=1; }
  [ "$desc_count" -ne 1 ] && { echo "FAIL  $name: expected exactly one 'description:' line, found $desc_count"; fail=1; }

  # 2. name: value has no trailing colon/junk (a bug caught twice by hand this session).
  if grep -qE '^name: .+: *$' "$f"; then
    echo "FAIL  $name: 'name:' value has a stray trailing colon"; fail=1
  fi

  # 3. frontmatter name matches the folder name.
  fm_name="$(grep -m1 '^name:' "$f" | sed 's/^name: *//')"
  if [ "$fm_name" != "$name" ]; then
    echo "FAIL  $name: frontmatter name '$fm_name' != folder name '$name'"; fail=1
  fi

  # 4. every code fence is closed (odd fence count = unclosed block).
  fence_count=$(grep -c '^```' "$f")
  if [ $((fence_count % 2)) -eq 1 ]; then
    echo "FAIL  $name: unclosed code fence (odd count: $fence_count)"; fail=1
  fi

  # 5. has a closing pitfalls/gotchas-style section — the consistent quality bar
  #    every skill in this repo follows.
  if ! grep -qE '^## Common Pitfalls' "$f"; then
    echo "WARN  $name: no '## Common Pitfalls' section (style convention, not a hard failure)"
  fi

  # 6. no obvious hardcoded secret patterns (a skill file is documentation —
  #    it should never contain a real credential, even an example one that
  #    looks plausible enough to be mistaken for real).
  if grep -qE '(AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)' "$f"; then
    echo "FAIL  $name: looks like it contains a real AWS key ID or private key block"; fail=1
  fi

  # 7. no leftover template placeholder text (copy-pasted from skill-template.md
  #    and never filled in).
  if grep -qE 'skill-name-in-kebab-case|Title In Title Case' "$f"; then
    echo "FAIL  $name: contains unfilled template placeholder text"; fail=1
  fi
done

# 8. duplicate names across the whole skill set.
dupes=$(grep -h "^name:" "$SKILLS_DIR"/*/SKILL.md | sort | uniq -d)
if [ -n "$dupes" ]; then
  echo "FAIL  duplicate skill name(s) across the repo:"
  echo "$dupes"
  fail=1
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "All checks passed ($(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ') skills)."

  # Auto-regenerate team dashboard if it exists (keeps agent inventory in sync).
  dashboard_gen="$(dirname "$0")/generate-team-dashboard.py"
  if [ -f "$dashboard_gen" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$dashboard_gen" 2>&1 | sed 's/^/  /'
  fi

  # Auto-regenerate Munder hire manifests if the generator exists (keeps the
  # 12 manager hires in sync with their agent-frontmatter descriptions).
  munder_gen="$(dirname "$0")/generate-munder-hires.py"
  if [ -f "$munder_gen" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$munder_gen" 2>&1 | sed 's/^/  /'
  fi

  # Auto-regenerate codex-fallback hires alongside (12 more, one per manager).
  fallback_gen="$(dirname "$0")/generate-fallback-hires.py"
  if [ -f "$fallback_gen" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$fallback_gen" 2>&1 | sed 's/^/  /'
  fi
else
  echo "One or more checks failed — see FAIL lines above."
fi
exit $fail
