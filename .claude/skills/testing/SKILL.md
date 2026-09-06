---
name: testing
description: Test strategy and test-writing discipline — the test pyramid, reproduce-then-fix for bugs, and testing infrastructure code. Use when writing tests, designing a test strategy, or deciding what level (unit/integration/e2e) a test belongs at.
---

# Testing

Stack-agnostic testing discipline. Applies to application code and, with adaptation, to infrastructure
code (see the infra-specific note below).

## The Pyramid (bottom-heavy by default)

- **Unit tests**: business logic in isolation — the majority of tests should live here; fast, no I/O,
  no network. If a piece of logic can be unit-tested, it should be, before reaching for integration/e2e.
- **Integration tests**: the boundaries — does the code correctly talk to a real (or realistic) database,
  API, queue, filesystem. Fewer than unit tests, but present for every genuine external boundary.
- **End-to-end tests**: full user-facing flows through the real system — fewest of all; expensive to
  write, slow to run, brittle to unrelated changes. Reserve for the critical paths that matter most, not
  as the default way to verify logic that could be unit-tested instead.

## Reproduce, Then Fix

For any bug fix: write a test that reproduces the bug first (it should fail against the current code),
then make the change that fixes it (the test now passes). This is the concrete form of `CLAUDE.md`
Section 1.4's "goal-driven execution" for bug fixes — it also guarantees the bug won't silently regress.

## Running the Existing Suite

Before and after any change, run the existing test suite — a change not verified against what already
exists isn't done, regardless of how confident the change looks on paper. If the suite is slow, run at
least the tests covering the changed area before a full run.

## Testing Infrastructure Code

- Terraform: `terraform plan` output is the closest equivalent to a test run for a given change — read it
  fully; `terraform validate` and `tflint` catch syntax/config errors; tools like Terratest exist for
  genuine automated infra test suites where the project has them.
- Kubernetes manifests: `kubectl apply --dry-run=server` and `helm template`/`helm install --dry-run`
  validate rendering and server-side admission without actually mutating the cluster.
- Ansible: `--check --diff` is the dry-run equivalent; `ansible-lint` catches common mistakes statically.
- CI/CD pipelines: a workflow can often be validated with a linter (`actionlint` for GitHub Actions) and,
  where available, run locally (`act`) before pushing.

## Common Pitfalls

- New logic shipped with no test, "because it's simple" — simple logic still regresses; the cost of a
  unit test is low relative to a silent regression later.
- End-to-end tests used to verify logic that unit tests could cover faster and more reliably — makes the
  suite slow and flaky without adding proportional confidence.
- A bug fixed without a reproducing test — the same bug (or a near-identical one) reappears later with no
  guard against it.
