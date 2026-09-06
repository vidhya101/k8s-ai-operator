---
name: crossplane
description: Crossplane — Kubernetes-native infrastructure composition via CRDs, as an alternative or complement to Terraform. Use when a platform-engineering setup provisions cloud infrastructure through Kubernetes control-plane resources rather than (or in addition to) Terraform.
---

# Crossplane

Extends the Kubernetes API to manage cloud infrastructure — cloud resources become Kubernetes custom
resources, reconciled continuously by controllers the same way a Deployment is. The main practical
difference from Terraform: Crossplane is a running control plane that continuously reconciles
(self-healing drift correction, like ArgoCD does for application manifests), where Terraform is
run-on-demand (`plan`/`apply`) unless wrapped in a separate automation loop.

## Core Concepts

- **Providers**: install support for a cloud (`provider-aws`, `provider-azure`, `provider-gcp`) — each
  registers CRDs for that cloud's resources (an S3 bucket becomes a `Bucket` custom resource, etc.).
- **Managed Resources (MRs)**: the direct 1:1 representation of a single cloud resource — the lowest-level
  building block, roughly analogous to a single Terraform resource block.
- **Compositions**: define how a higher-level, platform-team-authored abstraction (e.g. "a
  `PostgreSQLInstance`") maps to a set of underlying Managed Resources — this is Crossplane's answer to a
  Terraform module, but live and continuously reconciled rather than applied on demand.
- **Claims (XRCs)**: what application teams actually request (via a namespaced custom resource) against a
  platform-team-defined Composition — the self-service interface described in the `platform-engineering`
  skill, implemented concretely here.

## Example Shape

```yaml
# Platform team defines once:
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata: { name: xpostgresqlinstances.platform.example.org }
spec:
  group: platform.example.org
  names: { kind: XPostgreSQLInstance, plural: xpostgresqlinstances }
  claimNames: { kind: PostgreSQLInstance, plural: postgresqlinstances }
---
# Application team requests, self-service:
apiVersion: platform.example.org/v1alpha1
kind: PostgreSQLInstance
metadata: { name: my-app-db, namespace: my-app }
spec: { storageGB: 20, region: us-east-1 }
```

## When Crossplane Fits (vs. plain Terraform)

- A platform team building genuine self-service infrastructure (see `platform-engineering` skill) where
  application teams request infra via a Kubernetes-native API (fits naturally alongside GitOps/ArgoCD,
  since Crossplane resources are just more Kubernetes YAML ArgoCD can reconcile) — this is the strongest
  fit.
- Continuous drift correction is wanted for infrastructure the same way it's wanted for application
  manifests — Crossplane's controllers reconcile continuously; Terraform only corrects drift on the next
  `apply`.
- Don't introduce Crossplane just because it's newer — a team already effective with Terraform + a
  promotion pipeline doesn't need to add a second IaC paradigm without a specific driver (self-service via
  Kubernetes API, or wanting continuous reconciliation) — see Section 1.2, avoid speculative tooling.

## Common Pitfalls

- Running Crossplane and Terraform against the *same* cloud resources with no clear ownership boundary —
  both will fight over drift correction; partition by resource/environment, don't let both manage one thing.
- A Composition with no validation on the Claim's inputs, letting an application team's self-service
  request produce something outside intended guardrails (wrong region, oversized instance) — the whole
  point of the Claim/Composition split is enforcing guardrails at the platform layer.
- Provider credentials (cloud IAM) scoped too broadly for what the installed provider's managed resources
  actually need — same least-privilege principle as any other cloud automation.
