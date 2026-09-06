---
name: bash-scripting
description: Writing safe, robust Bash/shell scripts — strict mode, quoting, error handling, and portability. Use when writing or reviewing any shell script (automation glue, CI steps, hooks, cron jobs).
---

# Bash Scripting

Reference for writing shell scripts that fail loudly and predictably instead of silently doing the wrong
thing — the standard for anything from a CI step to a `.claude/hooks/` script in this repo.

## Strict Mode (default for any non-trivial script)

```bash
#!/usr/bin/env bash
set -euo pipefail
# -e: exit on any command failure (with documented exceptions — see below)
# -u: error on unset variable reference instead of silently expanding to empty
# -o pipefail: a pipeline fails if ANY stage fails, not just the last one
```

- `set -e` does **not** trigger inside an `if`/`while` condition, or for any command in an `&&`/`||` list
  except the last — this is standard and doesn't need a workaround, but it's a common source of confusion
  when a script "should have" exited but didn't.
- Where a command's failure is expected and handled, be explicit: `some_cmd || true` (only when the
  failure genuinely doesn't matter) or check `$?`/branch on it — don't disable `set -e` globally to work
  around one command.

## Quoting

- Quote every variable expansion: `"$var"`, not `$var` — unquoted expansion undergoes word-splitting and
  glob expansion, which breaks on any value containing a space, and is a classic source of both bugs and
  injection-style issues when the value comes from user input or another command's output.
- `"$@"` (quoted) to pass through all arguments preserving individual word boundaries — `$@` or `$*`
  unquoted collapses/splits them incorrectly.

## Error Handling & Traps

```bash
trap 'echo "failed at line $LINENO" >&2' ERR
cleanup() { rm -f "$tmpfile"; }
trap cleanup EXIT
tmpfile=$(mktemp)
```

- `trap ... EXIT` for cleanup that must run whether the script succeeds or fails (temp files, lock
  release) — more reliable than putting cleanup only at the end of the happy path.

## Portability

- `#!/usr/bin/env bash` over a hardcoded `#!/bin/bash` path — more portable across systems where bash
  isn't at a fixed location.
- Bash-specific syntax (`[[`, arrays, `local`) requires the bash shebang — a script using these but
  declared `#!/bin/sh` will break on systems where `/bin/sh` is dash/POSIX sh, not bash.
- `shellcheck` catches the large majority of quoting/portability/logic mistakes before they become
  production bugs — run it on every script of any real complexity.

## Common Pitfalls

- Parsing `ls` output instead of using globs (`for f in *.txt`) — `ls` output isn't designed for
  machine-parsing and breaks on filenames with spaces/special characters.
- A script that reads secrets from the environment and then `echo`s them for "debugging," leaking them
  into CI logs — see `.claude/rules/secrets.md`.
- Missing `set -e` on a script whose later steps depend on an earlier one succeeding, causing a silent
  cascade of failures that all get treated as if the earlier step worked.
- Comparing strings with `=` inside `[ ]` when a glob/pattern match was intended, or using `[ ]` when
  `[[ ]]`'s safer behavior (no word-splitting/glob-expansion on the operands) was needed.
