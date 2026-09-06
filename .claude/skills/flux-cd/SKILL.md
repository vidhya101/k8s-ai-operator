---
name: flux-cd
description: Flux CD — GitOps reconciliation as an alternative to ArgoCD, using Kubernetes-native CRDs (GitRepository, Kustomization, HelmRelease). Use when a project's GitOps operator is Flux instead of ArgoCD; see gitops and argocd for the shared GitOps concepts.
---

# Flux CD

The other major GitOps operator alongside ArgoCD (`argocd` skill) — same reconciliation model (`gitops`
skill's core principles apply identically: Git is the source of truth, CI stops at updating the Git repo,
never `kubectl apply` directly against a Flux-managed resource), different implementation and API shape.

## Core Resources

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata: { name: my-app, namespace: flux-system }
spec:
  url: https://github.com/org/my-app-config
  ref: { branch: main }
  interval: 1m
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata: { name: my-app, namespace: flux-system }
spec:
  sourceRef: { kind: GitRepository, name: my-app }
  path: "./overlays/prod"
  prune: true                    # remove resources deleted from Git — same semantics as ArgoCD's prune
  interval: 5m
```

- **`GitRepository`** (a `Source`) defines where to pull from; **`Kustomization`** (Flux's, not plain
  Kustomize's) defines what to apply from that source and how — the two-resource split is the main
  structural difference from ArgoCD's single `Application` resource.
- **`HelmRelease`** is Flux's equivalent of applying a Helm chart declaratively, pointing at a
  `HelmRepository` source the same way `Kustomization` points at a `GitRepository`.

## Key Commands (flux CLI)

```bash
flux get sources git                     # GitRepository sync status
flux get kustomizations                   # reconciliation status per Kustomization
flux diff kustomization my-app             # what would change on next reconcile — review before trusting
flux reconcile kustomization my-app         # force an immediate reconcile instead of waiting for `interval`
flux logs --follow                          # controller logs, useful for reconciliation failures
```

## Flux vs. ArgoCD — Practical Differences

- **UI**: ArgoCD ships a full web UI by default; Flux is CLI/API-first (a UI exists via Weave GitOps or
  third-party dashboards, but isn't as central to the base experience) — relevant to how a team will
  actually interact with sync status day to day.
- **Multi-tenancy model**: Flux's split Source/Kustomization/HelmRelease resources compose more granularly
  (different teams can own different `Kustomization`s pointing at a shared `GitRepository`); ArgoCD's
  `ApplicationSet` generators solve the equivalent fleet-management problem differently.
- Don't run both against the same cluster/resources with no ownership boundary — identical conflict risk
  to the `crossplane`-vs-Terraform and CloudFormation-vs-Terraform warnings elsewhere in this stack.

## Common Pitfalls

- `prune: true` enabled on a `Kustomization` pointed at a path that also contains pre-existing,
  non-Flux-managed resources — same first-sync pruning risk the `argocd` skill warns about.
- Reconciliation `interval` set too long for how quickly changes are expected to land, or too short for
  large repos, causing unnecessary Git polling load — tune against actual change frequency.
- Secrets committed in plaintext to a Flux-watched repo — same requirement as ArgoCD: use Sealed Secrets,
  External Secrets Operator, or SOPS (Flux has native SOPS decryption support), never a raw `Secret`.
- Not using `flux diff` before trusting a change will apply cleanly — same "review the plan before it
  applies" discipline as everywhere else in this stack, just via Flux's own diff mechanism.
