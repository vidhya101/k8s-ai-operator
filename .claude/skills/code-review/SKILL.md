---
name: code-review
description: General code review discipline — correctness, security, and scope, applied across any language or stack. Use when reviewing a diff/PR; pair with a stack-specific skill (terraform, docker, github-actions, ...) for tool-specific checks.
---

# Code Review

Stack-agnostic review discipline. Combine with the relevant tool-specific skill for infrastructure code
(`terraform`, `docker`, `github-actions`, etc.) — this skill covers what applies regardless of language.

## What to Check, in Priority Order

1. **Correctness**: does the change do what it claims? Trace the actual logic, don't just read the diff
   and infer intent from variable names.
2. **Security**: injection risks (SQL/command/template), auth/authz gaps, secrets, unsafe deserialization
   of untrusted input, SSRF/path traversal — check these explicitly, they're easy to miss in a read-through
   that's focused on business logic.
3. **Error handling at real boundaries**: exceptions/errors handled where failure can actually occur
   (network calls, file I/O, user input, external APIs) — not defensive handling for scenarios the code
   can't actually reach (see `CLAUDE.md` Section 1.2 — no error handling for impossible cases).
4. **Test coverage for the change**: does a test exist that would fail if this change were reverted or
   subtly wrong? A change with no test proving it works isn't verified, it's asserted.
5. **Scope discipline**: does every changed line trace to the stated purpose of the change, or did
   unrelated refactoring/renaming/formatting ride along (see `CLAUDE.md` Section 1.3, Surgical Changes)?

## Review Method

- Read the diff in the context of the surrounding file, not in isolation — a correct-looking change can
  be wrong given what's around it (an existing invariant it breaks, a caller that assumes old behavior).
- For a bug fix: confirm a test reproduces the original bug and passes after the fix (see `testing` skill).
- For infrastructure changes: the equivalent of a test is the plan/diff output (`terraform plan`,
  `kubectl diff`, `helm template` output) — read it fully, don't skim the summary line.
- Distinguish "this is wrong" from "this isn't how I'd have done it" — flag the former as blocking, the
  latter as an optional suggestion; don't block a correct change on style preference alone.

## Common Pitfalls (as a reviewer)

- Approving based on the PR description matching intent without reading the actual diff closely.
- Missing a security issue because the review focused entirely on whether the feature works.
- Nitpicking style/naming while missing a genuine correctness or security defect — prioritize findings by
  actual impact, and say so explicitly (e.g. "blocking" vs. "nit") so the important ones aren't diluted.
