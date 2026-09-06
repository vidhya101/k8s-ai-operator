---
name: pre-commit-hooks
description: The pre-commit framework — local git hooks that block unformatted code, lint violations, and secrets before a commit is created. Use when setting up or debugging .pre-commit-config.yaml; distinct from this setup's own .claude/hooks/ (which govern Claude's tool calls, not git commits).
---

# pre-commit (Local Git Hooks)

The `pre-commit` framework (pre-commit.com) manages git hooks declaratively — the shift-left layer that
catches formatting/lint/secret issues on a developer's machine, before they ever reach CI. This is a
different thing from this repository's own `.claude/hooks/` (which govern what Claude's tool calls are
allowed to do) — don't conflate the two when either is mentioned.

## Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0                       # pin a specific version, not a floating branch
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{ id: black }]

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks: [{ id: gitleaks }]          # secret scanning at commit time, not just in CI

  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.90.0
    hooks: [{ id: terraform_fmt }, { id: terraform_validate }, { id: terraform_tflint }]
```

```bash
pip install pre-commit
pre-commit install                    # activates the git hook in this local clone (one-time, per clone)
pre-commit run --all-files            # run every configured hook against the whole repo, not just staged
pre-commit autoupdate                 # bump hook revisions to latest
```

## Core Principles

- Pin every hook's `rev` — an unpinned/floating hook version can change behavior unexpectedly between
  runs, the same principle as pinning any other dependency.
- Keep pre-commit hooks fast (formatting, linting, secret scanning, basic syntax checks) — anything slow
  (full test suite, deep security scan) belongs in CI, not blocking every local commit.
- `pre-commit install` must be run per-clone — it's not automatically active just because the config file
  exists in the repo; a fresh clone with no one running `install` gets none of this enforcement locally
  (CI-side equivalents, e.g. `pre-commit run --all-files` in a CI job, are the backstop for this).
- Secret scanning at commit time (gitleaks/detect-secrets) catches a leak before it's even pushed —
  meaningfully earlier than catching it in CI or via GitHub secret scanning after the fact.

## Common Pitfalls

- Hooks configured but `pre-commit install` never run in a given clone, so the config silently does
  nothing locally — verify with `pre-commit run --all-files` rather than assuming it's active.
- A hook that mutates files (`black`, `terraform_fmt`) failing the commit on its first run because it
  reformatted files — this is expected behavior (re-stage and commit again), not a bug, but worth knowing
  before it looks like something broke.
- Hooks too slow/heavy, so developers start using `git commit --no-verify` to bypass them routinely —
  defeats the purpose; keep the local hook set fast enough that bypassing isn't the path of least
  resistance.
- No CI-side enforcement of the same checks — a developer who never ran `pre-commit install` locally gets
  no protection at all if CI doesn't also run `pre-commit run --all-files` as a backstop.
