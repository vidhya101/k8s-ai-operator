---
name: aws-native-cicd
description: AWS-native CI/CD and IaC — CodePipeline, CodeBuild, CodeDeploy, and CloudFormation. Use when a project's pipeline is built on AWS-native services instead of (or alongside) GitHub Actions/Jenkins and Terraform.
---

# AWS-Native CI/CD (CodePipeline, CodeBuild, CodeDeploy) & CloudFormation

The AWS-native alternative to GitHub Actions/Jenkins (`github-actions`/`jenkins` skills) for CI/CD, and to
Terraform (`terraform` skill) for IaC. Same design principles from `cicd-pipeline-design` apply — stage
sequencing, PR-vs-deploy separation, artifact immutability — just implemented with AWS's own services.

## CodePipeline (orchestration)

- Chains stages (Source → Build → Test → Deploy) with each stage's output as the next stage's input
  artifact — conceptually equivalent to a GitHub Actions workflow's job dependency chain, but AWS-native
  and integrated directly with other AWS services (CodeCommit/GitHub/S3 as source, CodeBuild/CodeDeploy/
  CloudFormation/ECS/Lambda as deploy targets) without needing OIDC federation since it runs natively
  within the account.
- Manual approval actions provide the human-gate equivalent of a GitHub Environment's required reviewers
  — same principle as `cicd-pipeline-design`'s PR-vs-merge separation, implemented as a pipeline stage.

## CodeBuild (build/test execution)

```yaml
# buildspec.yml
version: 0.2
phases:
  install: { commands: ["npm ci"] }
  build: { commands: ["npm run build", "npm test"] }
artifacts:
  files: ["**/*"]
  base-directory: dist
```

- Runs in an isolated, ephemeral managed build environment per build — same "ephemeral compute" principle
  as the `github-actions`/`jenkins` skills' preference for ephemeral runners, but AWS manages the
  lifecycle entirely.
- IAM role attached to the CodeBuild project scopes what the build can access (e.g. pull from ECR, read
  from S3) — least-privilege discipline applies identically to the OIDC-role pattern in `github-actions`.

## CodeDeploy (deployment orchestration)

- Supports in-place and blue/green deployments for EC2/on-prem, and blue/green or canary (via traffic
  shifting) for Lambda and ECS — the AWS-native mechanism for the same progressive-delivery patterns
  covered generically in `cicd-pipeline-design` and, for Kubernetes specifically, via Argo Rollouts/
  service mesh traffic splitting (`service-mesh` skill).
- Deployment hooks (`BeforeInstall`, `AfterInstall`, `ApplicationStart`, `ValidateService` for EC2;
  `BeforeAllowTraffic`/`AfterAllowTraffic` for Lambda/ECS) are the place for smoke tests before traffic
  fully shifts — a deployment with no `ValidateService`/`AfterAllowTraffic` hook has no automated check
  that the new version is actually healthy before it's considered "deployed."

## CloudFormation

- AWS-native declarative IaC, JSON/YAML — the direct alternative to Terraform for AWS-only infrastructure
  (no multi-cloud portability, but tighter native integration — e.g. CodePipeline can deploy a
  CloudFormation stack as a first-class action type without a wrapper).
- **Change sets**: CloudFormation's equivalent of `terraform plan` — always review a change set before
  executing it, same discipline as reviewing any other IaC plan (`terraform-best-practices` skill).
- **Drift detection**: CloudFormation can detect when live resources have diverged from the stack's
  template — run periodically or after any suspected manual change, the same concern the `gitops` skill
  addresses for Kubernetes.
- **Stack policies** protect specific resources from unintended updates/deletion during a stack update —
  worth setting on stateful resources (databases, buckets with data) the same way `terraform-reviewer`
  flags a plan that would replace/destroy a stateful resource.

## Common Pitfalls

- No manual approval stage before a production CodePipeline deploy action — the same "PR vs. deploy
  separation" gap the `github-actions` skill flags, just in AWS's own pipeline tool.
- CodeDeploy configured with no validation/rollback hook, so a broken deployment completes "successfully"
  with no automated health check catching it.
- CloudFormation stack updated by directly editing resources in the console "just this once," causing
  drift that the next real stack update either fights or gets confused by.
- Mixing CloudFormation and Terraform to manage the exact same resources with no ownership boundary — the
  same conflict the `crossplane` skill warns about between Crossplane and Terraform.
