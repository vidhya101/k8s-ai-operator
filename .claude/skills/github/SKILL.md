---
name: github
description: GitHub the platform — branch protection, CODEOWNERS, the gh CLI, Dependabot, and secret/code scanning. Use for GitHub-specific workflow/config questions distinct from Actions pipelines (see the github-actions skill for that) or core Git mechanics (see the git skill).
---

# GitHub (Platform)

GitHub-specific features beyond core Git mechanics (`git` skill) and beyond Actions pipelines
(`github-actions` skill) — repository configuration, review workflow, and built-in security tooling.

## Branch Protection & Review Workflow

- Protected branch rules (required reviews, required status checks, no force-push, no direct push) are
  how "PRs are required" actually gets enforced — evidence of these rules (or their absence) tells you
  whether to expect a PR-based workflow (see `.claude/rules/git-conventions.md`).
- `CODEOWNERS` file maps paths to required reviewers — check for one before assuming who should review a
  given change.
- Required status checks should include CI (tests, scans) before merge is allowed — a protected branch
  with no required checks only enforces "someone approved," not "it passed CI."

## Built-in Security Features

- **Dependabot**: automated dependency-update PRs + vulnerability alerts (`Security` tab /
  `dependabot.yml` for configuration) — complements but doesn't replace a dedicated SCA tool (`trivy`/
  `snyk` skills) since Dependabot's alert coverage and remediation-PR quality vary by ecosystem.
- **Secret scanning**: GitHub scans pushed content for known credential patterns and can push-protect
  (block a push containing a detected secret) if enabled — verify it's actually enabled, it's opt-in on
  many plans/repo visibility combinations.
- **Code scanning** (CodeQL or third-party): SAST results surfaced in the `Security` tab and as PR checks
  — check whether this is configured before assuming a repo has SAST coverage beyond `sonarqube`/other
  external tools.

## `gh` CLI

```bash
gh pr view <number> / gh pr list / gh pr diff <number> / gh pr checks <number>
gh pr create --title "..." --body "..."          # mutating — confirm first
gh issue list / gh issue view <number>
gh run list / gh run view <run-id> --log-failed    # Actions run inspection
gh api <endpoint>                                  # raw REST API access for anything not covered above
gh secret list                                      # names only, never prints values
```

## GitHub Packages / Container Registry

- GHCR (see the `ghcr` skill) is GitHub's package/container registry, tied to repo/org permissions —
  distinct from Dependabot/secret scanning, but often configured together as part of the same supply-
  chain posture.

## Common Pitfalls

- Branch protection present but with no required status checks, or checks configured but not marked
  "required" — merge is possible with a red CI run.
- `CODEOWNERS` present but a path pattern doesn't match the actual directory structure (a common typo
  source), silently leaving files without an enforced reviewer.
- Secret scanning enabled for alerting but push-protection not enabled, so a leaked secret is detected
  after it's already in history rather than blocked at push time.
- Treating Dependabot alerts as equivalent coverage to a dedicated SCA/container scan — its ecosystem and
  depth of coverage varies and shouldn't be assumed to be a complete substitute.
