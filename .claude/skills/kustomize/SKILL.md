---
name: kustomize
description: Kustomize — template-free Kubernetes manifest customization via base/overlay patching. Use when a project manages Kubernetes manifests with Kustomize instead of (or alongside) Helm; common in ArgoCD-managed GitOps repos.
---

# Kustomize

Patches plain Kubernetes YAML per environment without templating — a `base` defines the common manifest,
`overlays` patch it per environment. Built into `kubectl` (`kubectl apply -k`) and natively understood by
ArgoCD (see the `argocd`/`gitops` skills).

## Structure

```text
base/
  kustomization.yaml
  deployment.yaml
  service.yaml
overlays/
  dev/
    kustomization.yaml       # references ../../base, patches for dev
  prod/
    kustomization.yaml       # references ../../base, patches for prod
```

```yaml
# base/kustomization.yaml
resources:
  - deployment.yaml
  - service.yaml

# overlays/prod/kustomization.yaml
resources:
  - ../../base
patches:
  - target: { kind: Deployment, name: my-app }
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 5
images:
  - name: my-app
    newTag: v1.2.3
configMapGenerator:
  - name: my-app-config
    literals:
      - LOG_LEVEL=info
```

## Core Principles

- Base manifests should be genuinely environment-agnostic — anything that differs per environment
  (replica count, resource limits, image tag, config values) belongs in an overlay patch, not hardcoded
  in the base with a comment saying "change this for prod."
- `configMapGenerator`/`secretGenerator` append a content hash to the generated resource's name by
  default, and Kustomize automatically updates references to the new name — this is what makes a
  ConfigMap change actually trigger a rolling update of pods that mount it (a plain, unhashed ConfigMap
  edit doesn't).
- Strategic merge patches (`patchesStrategicMerge`, older syntax) vs. JSON 6902 patches (`patches` with
  `op`/`path`, current syntax) — prefer the JSON patch form for precision (exact field targeting); use
  strategic merge for broader, additive changes where it reads more naturally.

## Key Commands

```bash
kustomize build overlays/prod                 # render final manifests, review before applying
kubectl apply -k overlays/prod                # apply directly (bypasses GitOps if used outside ArgoCD)
kubectl kustomize overlays/prod                # same as `kustomize build` via the built-in kubectl plugin
```

Always `build`/render and review before `apply` — same discipline as reviewing a `terraform plan` or
`helm template` output before applying it.

## Kustomize vs. Helm

- Kustomize: no templating language, patches real YAML — easier to review (it's still just Kubernetes
  YAML), less powerful for conditional/complex logic.
- Helm: full templating language, packaging (`Chart.yaml`, versioning, a public/private chart repo) —
  better for distributing a reusable chart to third parties, more powerful but harder to review by eye.
- They can be combined (Helm chart rendered via `helm template`, then further patched by Kustomize) —
  check which pattern a repo already uses before introducing the other.

## Common Pitfalls

- A secret's plaintext value committed via `secretGenerator`'s `literals:`/`files:` — same "never commit
  a real secret" rule as anywhere else; use `--disableNameSuffixHash` awareness aside, the actual values
  still land in git unless sourced from a secret manager reference instead.
- Overlay patches accumulating so much divergence from the base that the "shared base" no longer reflects
  what's actually common — a signal the base/overlay split needs rethinking, not more patches.
- Forgetting that `configMapGenerator` changes the resource name (via hash suffix) — a manually-written
  reference to the old fixed name elsewhere in the manifests breaks instead of being auto-updated.
