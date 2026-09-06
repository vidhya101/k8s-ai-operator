---
name: azure-devops
description: Azure DevOps — Pipelines (YAML), Boards, and Repos. Use when the CI/CD and project-tracking platform is Azure DevOps rather than GitHub/GitHub Actions.
---

# Azure DevOps (Pipelines, Boards, Repos)

Microsoft's integrated CI/CD + work-tracking + repo platform — the Azure-native alternative to GitHub +
GitHub Actions. Same pipeline design principles from `cicd-pipeline-design` apply; this covers Azure
DevOps-specific mechanics.

## Pipelines (YAML)

```yaml
trigger:
  branches: { include: [main] }
pr:
  branches: { include: [main] }          # separate trigger for PR validation vs. merge-triggered deploy

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        pool: { vmImage: ubuntu-latest }
        steps:
          - script: npm ci && npm test
          - task: PublishBuildArtifacts@1

  - stage: Deploy
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployProd
        environment: production          # environment approvals/checks gate here
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "deploy"
```

- `trigger`/`pr` sections separate what runs on a PR (validation only) from what runs on merge (can
  deploy) — same PR-vs-merge boundary as GitHub Actions, expressed differently.
- **Environments** with approvals and checks are the Azure DevOps equivalent of a GitHub Environment's
  required reviewers — a production `environment:` with no approval check is the same gap the
  `github-actions-reviewer` agent flags for a GitHub Actions deploy job with no required-reviewer environment.
- **Service connections** are how a pipeline authenticates to Azure/AWS/GCP/other services — prefer
  workload-identity-federation-based service connections (no stored secret) over a service principal with
  a stored client secret, same OIDC-over-static-credentials principle as `github-actions`.
- **Variable groups** (optionally backed by Azure Key Vault) for shared config/secrets across pipelines —
  never hardcode a secret directly in pipeline YAML.

## Boards

- Work item tracking (Epics/Features/User Stories/Tasks/Bugs) with configurable process templates (Agile/
  Scrum/CMMI) — relevant mainly for understanding a team's existing workflow/ticket-linking convention
  before assuming a different one (e.g. don't assume GitHub Issues conventions apply if a repo is
  Azure-DevOps-tracked).

## Repos

- Git-compatible — standard `git` mechanics (see the `git` skill) apply directly; branch policies
  (required reviewers, required builds passing, linked work items) are Azure DevOps Repos' equivalent of
  GitHub branch protection rules (see the `github` skill's branch protection section for the same
  underlying concept).

## Common Pitfalls

- No separate `pr:` trigger, so PR builds and merge builds run identical pipelines with no distinction —
  a PR pipeline should validate only, not carry deploy stages that could run against untrusted PR code.
- A service principal with a long-lived stored secret used for a service connection instead of workload
  identity federation, when the target cloud supports it.
- Environment checks/approvals not configured, so `environment: production` reads as gated but isn't
  actually enforcing anything.
- Variable group secrets referenced but the pipeline's YAML not marked to treat them as secret
  (`isSecret`), risking accidental exposure in logs.
