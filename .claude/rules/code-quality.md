# Rule: Code Quality Standards

Applies to every `code-writer-*` sub-agent's output, and to every direct code change any agent
makes. Enforced by `code-reviewer` at review time — failure to meet these is a blocking finding,
not a nit.

## Error handling

- Every call that can genuinely fail (network, file I/O, subprocess, external API, DB query,
  parse of untrusted input) has its failure handled explicitly.
- The failure mode is NAMED — you handle `IOError` or `ConnectionRefusedError` specifically,
  not a bare `except:` / `catch (Exception e)` that swallows everything.
- Handling doesn't mean silently succeeding. Log with context, propagate up with wrapping, or
  return a typed failure — never catch-and-ignore.
- Retries only where the operation is genuinely idempotent, with backoff, and with a bounded
  retry count. A retry loop with no ceiling is a DoS-on-self.

## Exception handling

- Reserve exceptions (throw/raise) for genuinely unexpected conditions — programmer errors,
  unrecoverable state. Expected failures use typed returns (`Result<T, E>`, `Optional`, error
  as second return value in Go).
- A top-level handler that logs-and-crashes is fine and often correct for a service on startup
  failure; a top-level handler that logs-and-continues is almost never correct.

## Commenting

- Comments explain **WHY**, not WHAT. `// increment counter` is noise; `// we increment before
  the check because <race condition explanation>` is signal.
- **Docstrings** on public API surface: functions, classes, modules that will be called from
  elsewhere. Follow the language's standard convention (PEP 257 / JSDoc / godoc / Javadoc /
  TSDoc).
- Don't add documentation nobody asked for across a whole file just because you were editing
  one function — match the scope of the change.

## Double-checking / verification

- Every non-trivial change goes through `code-reviewer` (language quality) AND `tester`
  (functional coverage) AND `sandbox-verifier` (real-environment behavior) before it's
  considered done.
- "The code compiles" is not verification. "The tests pass" is partial verification. "The
  scratch-env deploy behaves as designed" is verification.

## Scope discipline (see CLAUDE.md Section 1.3)

- Every changed line traces to the stated purpose of the change. No drive-by refactors, no
  dependency bumps, no style fixes unrelated to what was asked.
- Cleanups introduced BY your change (an import that's now unused because you removed the
  caller) are yours to clean. Pre-existing cleanup opportunities you notice: mention, don't
  silently sweep in.

## Security defaults

- Never hardcode secrets. Use env vars, secret managers, or the platform's native mechanism.
  See `.claude/rules/secrets.md`.
- Never build SQL / shell commands / templates by string concatenation of user input. Use
  parameterized queries / arg lists / template engines that escape by default.
- Validate untrusted input at the boundary — size limits, type checks, allowlist over denylist
  where possible.
- Fail closed: on ambiguity, reject rather than proceed.

## Self-learning (via memory)

- After completing significant work, write findings to memory per `.claude/rules/memory-usage.md`
  so future sessions benefit. Includes: solutions to non-obvious problems, gotchas discovered,
  decisions made.
- Before starting significant work, read memory for prior context on this project/class of task.
  Don't re-derive what a prior session already learned.

## No frivolous files

Prefer editing existing files. Create a new file only when:

- an obvious module boundary demands it (new domain, new public API surface)
- the existing file would materially exceed the language's norm (>500 LOC
  for Python/TS/Go; >800 for Java; adjust for reason)
- convention dictates it (a new test file for a new module, a new ADR for a
  new decision, a new migration for a new schema change)

Do NOT create files "for organization" when a reader would prefer to see the
code together. Do NOT create README/CHANGELOG/CONTRIBUTING for a folder that
has no external audience. Do NOT split a 50-line class across three files.
Do NOT scaffold a directory of empty placeholder files "for later".

If you are about to create the FOURTH new file for a task the user asked as
one sentence — stop. That is almost always over-decomposition. Consolidate
and reconsider whether the split earns its cost in reader effort.

## Applies to

Every `code-writer-*` agent's output. Every direct code write by any agent. The `code-reviewer`
enforces this at review — findings above the low threshold block, per the reviewer's discipline.

## Cross-reference

- `.claude/rules/safety.md` — mutating operations, blast-radius confirmation
- `.claude/rules/secrets.md` — credential handling
- `code-review` skill — reviewer discipline detail
- `testing` skill — test pyramid, reproduce-then-fix
