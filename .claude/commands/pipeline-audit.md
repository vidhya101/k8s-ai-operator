---
description: Audit CI/CD pipeline definitions (GitHub Actions/Jenkins) for security, efficiency, and correctness.
argument-hint: "[optional: specific workflow file]"
---

Audit the CI/CD pipeline(s) at: $ARGUMENTS (default: `.github/workflows/*` and any `Jenkinsfile`).

Delegate to the `github-actions-reviewer` agent using the `github-actions` skill (or the `jenkins` skill
for Jenkinsfiles). Check specifically for:

- Unpinned third-party actions/plugins (tag instead of commit SHA)
- Overly broad `permissions:` blocks or missing `permissions:` entirely
- Long-lived cloud credentials in secrets instead of OIDC federation
- Whether PR-triggered jobs can mutate infrastructure (they should only plan/test, never apply/deploy)
- Missing required reviewers/environments on production-deploying jobs
- Caching correctness and whether secrets could leak into a cache
- Whether runners are ephemeral/autoscaling or static or self-hosted with unclear ownership

Report findings ranked by severity, each with the exact file and line.
