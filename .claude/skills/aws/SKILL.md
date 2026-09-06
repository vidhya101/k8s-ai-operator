---
name: aws
description: AWS-specific cloud engineering — account/org structure, IAM, VPC design, and common service selection. Use when the target cloud is AWS and the question isn't specific to Terraform/EKS (see those skills for IaC/K8s specifics on AWS).
---

# AWS

General AWS cloud-engineering reference. Pair with `terraform` for provisioning and `eks` for Kubernetes.

## Account Structure

- AWS Organizations with an account-per-environment (or account-per-team) model for blast-radius and
  billing isolation — a single-account setup is fine for a small/early-stage project but should be called
  out as a scaling limit if the project is growing.
- Service Control Policies (SCPs) at the OU level for guardrails (e.g. deny leaving a region, deny
  disabling CloudTrail) that apply regardless of IAM permissions within the account.
- AWS Control Tower or a landing-zone Terraform module for standardized new-account provisioning at scale.

## IAM

- Roles (assumed, temporary credentials) over IAM users with long-lived access keys, wherever possible.
- IRSA/Pod Identity for EKS workloads, OIDC federation for CI (see `github-actions` skill) — avoid static
  access keys as a first resort.
- Policies scoped to specific resource ARNs and actions; avoid `"Resource": "*"` / `"Action": "*"` unless
  there's a specific, reviewed reason.

## Networking

- VPC per environment (or per account, if account-per-environment); plan CIDR ranges to avoid overlap
  before any VPC peering or Transit Gateway connectivity is needed later.
- Public subnets only for resources that must be internet-facing (load balancers, NAT gateways);
  application/database tiers in private subnets with routes through a NAT gateway for outbound-only access.
- Security groups as the primary segmentation tool; default-deny (no inbound rule = no access) plus
  explicit allows, not broad `0.0.0.0/0` ingress on anything but a public-facing load balancer's intended
  ports.

## IAM Permission Boundaries

- A Permission Boundary caps the *maximum* permissions an IAM role/user can ever have, even if its
  attached policies grant more — used to let a team self-service-create roles (e.g. via Terraform/
  Crossplane in a platform-engineering setup) without being able to escalate beyond the boundary. Distinct
  from an SCP (which applies at the AWS Organizations level, across accounts) — a Permission Boundary
  applies to a specific principal within one account.

## Event-Driven Automation: EventBridge + Lambda

- EventBridge routes AWS resource state-change events (a new S3 bucket created, a security group rule
  changed, a non-compliant resource detected by AWS Config) to a target — commonly a Lambda function that
  reacts automatically (tag the resource, notify, or remediate).
- This is real, standing infrastructure (an EventBridge rule + a deployed Lambda), not something wired up
  ad hoc — treat a rule that *automatically remediates* (e.g. auto-deletes or auto-revokes access on a
  non-compliant resource) with the same caution as any other unattended-mutating-automation: it needs its
  own tested rollback path and should very likely notify/alert before or alongside acting, not act silently.
  Auto-*detection* and alerting is low-risk and broadly safe to automate; auto-*remediation* against live
  infrastructure is a decision to make deliberately with the user, not something to wire up by default —
  see `.claude/rules/safety.md`.

## Key CLI

```bash
aws sts get-caller-identity                     # confirm which account/role you're actually operating as
aws organizations list-accounts
aws ec2 describe-vpcs / describe-subnets / describe-security-groups
aws iam list-attached-role-policies --role-name <role>
aws cloudtrail lookup-events --lookup-attributes ...
```

## Common Pitfalls

- Root account used for day-to-day operations instead of being locked down with MFA and used only for
  the handful of actions that require it.
- CloudTrail not enabled account-wide, or not sent to a centralized/immutable log destination, leaving no
  audit trail after an incident.
- Cost allocation tags missing, making it impossible to attribute spend to a team/project after the fact.
