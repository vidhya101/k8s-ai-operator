---
name: cicd-pipeline-design
description: Tool-agnostic CI/CD pipeline design principles — stage sequencing, environment promotion, and artifact immutability. Use when designing a pipeline's overall shape before committing to GitHub Actions/Jenkins/GitLab CI specifics, or when comparing pipeline tools.
---

# CI/CD Pipeline Design

The design principles behind a good pipeline, independent of which tool implements it — see
`github-actions`/`jenkins` for tool-specific mechanics, and `CLAUDE.md` Section 2 for how this fits into
the broader onboarding-then-build workflow.

## Stage Sequencing

```text
1. Lint/format        — fastest feedback, catches trivial issues before anything expensive runs
2. Unit test            — fast, no external dependencies
3. Build                — compile/package/multi-stage Docker build
4. Scan                 — SAST, SCA, image scan, IaC scan (see devsecops skill for gate placement)
5. Integration test      — against real/realistic dependencies, slower, run after build confirms it's
                            worth the time
6. Push artifact          — only after every gate above passes; tag immutably (git SHA, not `latest`)
7. Deploy (promote)        — to the next environment, via GitOps (see gitops skill) not direct mutation
8. Smoke test/verify        — confirm the deployed change is actually healthy before calling it done
```

Order matters for cost: put cheap, fast checks before expensive, slow ones so a trivial mistake fails in
seconds, not after a 10-minute integration test suite.

## Environment Promotion

- A build artifact (container image, package) should be built **once** and promoted unchanged across
  environments (dev → stage → prod) — rebuilding per environment risks the artifact that reaches
  production differing from what was actually tested.
- Promotion is a deployment/config change (bump an image tag, merge a promotion PR), not a rebuild.
- Environment-specific values (secrets, endpoints, replica counts) live in environment-specific config
  (Helm values, Kustomize overlays, environment variables) layered onto the same artifact — never baked
  into the artifact itself.

## Artifact Immutability

- Tag every artifact with something immutable (git SHA, or SHA + semver) — a mutable tag (`latest`, a
  branch name) means "what's running" can silently change underneath a deployment that didn't intend to
  change anything.
- Once pushed, an artifact's tag should never be overwritten — if a rebuild is needed, it gets a new tag.

## PR vs. Merge Separation

- Anything triggered by a pull request (untrusted or in-review code) should only run read-only/advisory
  stages: lint, test, scan, plan. Only a merge to a protected branch (or an explicit release trigger)
  should reach deploy/apply/push stages — this boundary is what prevents an unreviewed change from
  reaching production.

## Common Pitfalls

- A pipeline that rebuilds the artifact at each promotion stage instead of promoting the same build —
  "works in staging" stops meaning anything if prod runs a different build.
- No smoke test after deploy — the pipeline reports success the moment `kubectl apply`/`helm upgrade`
  returns, even if the new pods are crash-looping.
- Environment secrets baked into the build artifact instead of injected at deploy time, making the same
  artifact unable to move between environments without a rebuild.
- Slow stages (full integration/e2e suites) placed before fast stages (lint/unit test), wasting CI minutes
  on runs that a 10-second lint check would have failed anyway.
