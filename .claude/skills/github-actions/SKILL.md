---
name: github-actions
description: Author and review GitHub Actions workflows — job/permission design, OIDC to cloud providers, caching, and self-hosted autoscaling runners. Use when writing or debugging .github/workflows files.
---

# GitHub Actions

CI/CD workflow authoring reference. See the `github-actions-reviewer` agent for a structured security/
efficiency review pass.

## Workflow Shape

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read           # least privilege by default; widen per-job only where needed

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<pinned-sha>
      - uses: actions/setup-node@<pinned-sha>
        with: { node-version: '20' }
      - run: npm ci
      - run: npm test

  deploy:
    if: github.ref == 'refs/heads/main'   # only main, never a PR, can reach deploy
    needs: [test]
    runs-on: ubuntu-latest
    environment: production               # required reviewers gate here
    permissions:
      id-token: write                     # for OIDC
      contents: read
    steps:
      - uses: actions/checkout@<pinned-sha>
      - uses: aws-actions/configure-aws-credentials@<pinned-sha>
        with:
          role-to-assume: arn:aws:iam::<account>:role/<deploy-role>
          aws-region: <region>
      - run: <deploy step>
```

## Matrix Builds, Artifacts, and Reuse

```yaml
jobs:
  test:
    strategy:
      matrix:
        node: [18, 20]
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/setup-node@<pinned-sha>
        with: { node-version: "${{ matrix.node }}" }
      - run: npm test
      - uses: actions/upload-artifact@<pinned-sha>
        with: { name: coverage-${{ matrix.os }}-${{ matrix.node }}, path: coverage/ }

  publish:
    needs: [test]
    steps:
      - uses: actions/download-artifact@<pinned-sha>   # pull what an earlier job uploaded
        with: { name: coverage-ubuntu-latest-20 }
```

- **Matrix** (`strategy.matrix`) runs the same job across a combinatorial set of inputs (versions, OSes)
  in parallel — the standard way to test across multiple runtime versions without duplicating job
  definitions; `fail-fast: false` if one matrix leg failing shouldn't cancel the others.
- **Artifacts** (`upload-artifact`/`download-artifact`) pass files between jobs (which otherwise run on
  independent, isolated runners with no shared filesystem) — job `outputs:` (small string values via
  `$GITHUB_OUTPUT`) are the equivalent mechanism for passing small data rather than files.
- **Composite actions** (`action.yml` with `runs.using: composite`) bundle a repeated sequence of steps
  into one reusable action, referenced with `uses: ./.github/actions/my-action` or from another repo.
- **Reusable workflows** (`on: workflow_call` in the called workflow, `uses: org/repo/.github/workflows/
  x.yml@ref` in the caller) share an entire job/workflow definition across repos — the difference from a
  composite action is scope: a composite action is a step-level building block, a reusable workflow is a
  whole job-level one, with its own `secrets:`/`with:` interface.

## OIDC to Cloud Providers (preferred over static credentials)

- AWS: `aws-actions/configure-aws-credentials` with `role-to-assume`, no `AWS_ACCESS_KEY_ID` secret needed.
- Azure: `azure/login` with `client-id`/`tenant-id`/`subscription-id` and federated credential configured
  on the Azure AD app, no client secret needed.
- GCP: `google-github-actions/auth` with Workload Identity Federation, no downloaded service account key.

## Self-Hosted Autoscaling Runners

- GitHub Actions Runner Controller (ARC) on Kubernetes, or an autoscaling EC2/VM runner group, for cost
  control and workloads needing more compute/specific tooling than hosted runners provide.
- Ephemeral runners (one job per runner, then destroyed) prevent state/secret leakage between jobs —
  prefer this over long-lived static self-hosted runners.

## Key Commands / Checks

```bash
gh workflow list
gh run list --workflow=<file>
gh run view <run-id> --log-failed
gh secret list
act -j <job> -W .github/workflows/<file>.yml    # local dry-run, if `act` is available
```

## Common Pitfalls

- `pull_request_target` used to get write permissions/secrets while still checking out and running
  untrusted PR code — a code-injection path into secrets/production; use `pull_request` for untrusted
  code, and if `pull_request_target` is truly needed, never check out and execute the PR's own code.
- Actions pinned to a tag (`@v4`) instead of a commit SHA — tags are mutable and can be repointed.
- A deploy job reachable from a `pull_request` trigger instead of gated to `push`/`main` — lets a PR
  mutate infrastructure before review.
- Secrets interpolated directly into a `run:` shell command via `${{ secrets.X }}` instead of passed
  through `env:` — the former is vulnerable to shell injection from untrusted context values.
