---
name: checkov
description: Policy-as-code scanning for IaC with Checkov — Terraform, CloudFormation, Kubernetes manifests, Helm, and Dockerfiles. Use when scanning IaC for misconfiguration before apply/deploy.
---

# Checkov

Static policy analysis across IaC formats — the standard gate before `terraform apply` or before a K8s
manifest reaches a GitOps repo (see `CLAUDE.md` Section 9).

## Usage

```bash
checkov -d .                              # scan a directory, auto-detects framework (tf, k8s, Dockerfile...)
checkov -f main.tf                        # single file
checkov -d . --framework terraform         # scope to one framework explicitly
checkov -d . --check CKV_AWS_20            # run a specific check only
checkov -d . --skip-check CKV_AWS_8        # skip a specific check (requires a justification elsewhere)
checkov -d . --compact                     # condensed output
checkov -d . -o json > results.json        # machine-readable output for pipeline gating
```

## Suppression (must be justified)

```hcl
# checkov:skip=CKV_AWS_20:Public bucket is intentional — this hosts a public static site (ticket INFRA-123)
resource "aws_s3_bucket" "public_site" { ... }
```

Every skip needs the reason inline, ideally linked to a ticket — an unexplained skip is treated as its
own finding by the `terraform-reviewer`/`security-auditor` agents, not as "handled."

## What It Catches (representative, not exhaustive)

```text
- Public S3/Storage/GCS bucket access
- Missing encryption at rest (databases, volumes, buckets)
- Security groups/NSGs open to 0.0.0.0/0
- IAM policies with wildcard actions/resources
- Missing logging/audit trail (CloudTrail, Activity Log, Audit Logs)
- Kubernetes: containers running as root, missing resource limits, privileged containers,
  missing NetworkPolicy default-deny
```

## Pipeline Placement

- Run against every `terraform plan` before apply, and against rendered Kubernetes manifests
  (`kubectl apply --dry-run` / `helm template` output) before they land in a GitOps repo.
- Block on findings at/above the agreed severity (commonly HIGH/CRITICAL) — confirm the exact threshold
  with the user; don't assume a default.

## Common Pitfalls

- Scanning source `.tf` files but never the rendered plan — some misconfigurations only become apparent
  with variable values resolved (e.g. a variable that could make a bucket public depending on env).
- A skip comment added to unblock a deploy under time pressure, with the intent to "fix it later" and no
  ticket created — becomes permanent technical/security debt.
- Running Checkov locally but not wired into CI, so it catches nothing for anyone who doesn't remember to
  run it manually.
