---
name: gcp
description: GCP-specific cloud engineering — resource hierarchy (org/folder/project), IAM, VPC design, and service account best practices. Use when the target cloud is GCP and the question isn't specific to Terraform/GKE (see those skills for IaC/K8s specifics on GCP).
---

# GCP

General GCP cloud-engineering reference. Pair with `terraform` for provisioning and `gke` for Kubernetes.

## Resource Hierarchy

- Organization → folders (often per team/environment) → projects as the isolation and billing unit —
  a project is the natural blast-radius boundary in GCP, similar to an AWS account.
- Organization Policies at the org/folder level for guardrails (e.g. restrict allowed locations, disable
  service account key creation) that apply regardless of IAM grants within a project.
- One project per environment per service (or per environment for a small system) rather than mixing
  dev/prod resources in a single project.

## Identity: IAM & Service Accounts

- Workload Identity Federation for GKE pods (see `gke` skill) and for external workloads (CI, on-prem)
  authenticating to GCP without a downloaded service account key JSON file.
- Service account keys (downloadable JSON) are a last resort — prefer Workload Identity Federation or
  attaching a service account directly to the compute resource (GCE instance, Cloud Run service).
- IAM roles bound at the project (or more narrowly, resource) level using predefined roles before custom
  roles; avoid `roles/owner`/`roles/editor` grants to service accounts or CI identities.

## Networking

- VPC per environment, or shared VPC (host project + service projects) for centralized network
  administration across multiple projects — decide based on whether network ops should be centralized
  or per-team.
- Firewall rules are VPC-wide (not subnet-scoped like AWS security groups) and tag/service-account based
  — plan tagging conventions before writing many overlapping rules.
- Private Google Access / Private Service Connect for reaching Google APIs and other services without
  traversing the public internet.

## Key CLI

```bash
gcloud config list                                # confirm active project/account
gcloud projects list
gcloud compute networks list / subnets list / firewall-rules list
gcloud projects get-iam-policy <project>
gcloud logging read "logName:activity" --limit 20  # Cloud Audit Logs
```

## Common Pitfalls

- Service account JSON keys created and distributed instead of using Workload Identity Federation —
  a leaked key has no built-in expiry unless explicitly rotated.
- A firewall rule with an overly broad target (`0.0.0.0/0` source, or applied via a broad network tag
  many unrelated instances share) instead of scoped to the specific service account/tag that needs it.
- Billing/quota alerts not configured at the project or org level, allowing a runaway resource to scale
  cost unnoticed until the invoice arrives.
