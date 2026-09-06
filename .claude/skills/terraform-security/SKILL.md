---
name: terraform-security
description: Security-review Terraform code — IAM least privilege, encryption, public exposure, secrets handling, and policy-as-code scanning with Checkov/tfsec. Use when reviewing IaC for security before apply, or auditing existing infrastructure code.
---

# Terraform Security

Security review of infrastructure-as-code, independent of which cloud it targets.

## Core Principles

- Least privilege by default: no `*` action/resource in IAM policies unless explicitly justified.
- Encryption at rest and in transit enabled by default for anything storing or moving data.
- No resource exposed to the public internet unless that's the explicit, stated intent (a load balancer
  or CDN — not a database, cache, or internal API).
- No secret value ever written into `.tf`/`.tfvars`, even "temporarily" — use a secret manager data source.
- Every IAM/RBAC grant should be traceable to a specific need, not "grant broadly to avoid follow-up tickets."

## What to Check

```text
- Storage (S3/Blob/GCS buckets): public access blocked by default, encryption enabled,
  versioning + lifecycle policy for anything with a retention requirement, access logging enabled
- Databases: not publicly reachable, encryption at rest enabled, automated backups configured,
  credentials sourced from a secret manager not a tfvars file
- IAM/RBAC: no wildcard resource/action, no long-lived access keys where a role/managed identity
  would work, trust policies scoped to the specific principal that needs them
- Networking: security groups/NSGs/firewall rules reviewed for 0.0.0.0/0 ingress on anything but
  a public load balancer's intended ports
- Logging/audit: CloudTrail/Activity Log/Audit Logs enabled at the account/subscription/project level
```

## Scanning

```bash
checkov -d .              # policy-as-code scan across providers
checkov -f main.tf         # single file
tflint                     # provider-aware linting, catches invalid configs checkov may miss
```

Treat a Checkov `FAILED` on encryption, public access, or logging as blocking by default; anything more
nuanced (e.g. a specific compliance framework check) — confirm the required severity threshold with the
user rather than assuming.

## Common Pitfalls

- A security group opened to `0.0.0.0/0` "temporarily for testing" that ships to the reviewed plan.
- Encryption configured on the resource but the KMS/encryption key itself has an overly broad key policy.
- IAM least-privilege applied to the role but the *trust policy* (who can assume it) left wide open.
- A suppressed Checkov finding (`#checkov:skip=`) with no linked justification — treat as its own finding.
