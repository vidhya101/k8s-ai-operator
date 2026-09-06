---
name: helm
description: Author and review Helm charts — templating, values structure, chart dependencies, and release management. Use when writing or reviewing a Helm chart, or debugging a failed helm install/upgrade.
---

# Helm

Kubernetes package manager and templating engine. Charts are typically what a GitOps tool (see `argocd`
skill) points at, rather than being installed directly against production.

## Chart Structure

```text
mychart/
  Chart.yaml          # name, version, appVersion, dependencies
  values.yaml          # default values — should be sane defaults, not empty stubs
  values-<env>.yaml     # optional per-environment overrides, layered with -f
  templates/
    deployment.yaml
    service.yaml
    _helpers.tpl        # shared template snippets (labels, names)
  charts/               # vendored subchart dependencies (via `helm dependency build`)
```

## Core Principles

- `values.yaml` defaults should let the chart install and run without requiring every consumer to
  override everything — override only what genuinely differs per environment.
- Use `_helpers.tpl` for repeated label/name logic instead of duplicating template snippets everywhere.
- Pin the chart's own `version` (semver) and bump it on every change — chart version and `appVersion`
  (the version of the app it deploys) are independent fields, don't conflate them.
- `helm template`/`helm install --dry-run` before a real install/upgrade to catch templating errors and
  review the actual rendered manifests, not just the chart source.

## Key Commands

```bash
helm lint ./mychart
helm template ./mychart -f values-prod.yaml          # render without installing, review output
helm install --dry-run --debug <release> ./mychart -f values-prod.yaml
helm list -n <ns>
helm status <release> -n <ns>
helm get values <release> -n <ns>                     # what values are actually deployed right now
helm diff upgrade <release> ./mychart -f values.yaml  # requires helm-diff plugin — preview before upgrade
helm rollback <release> <revision> -n <ns>
```

## Common Pitfalls

- Hardcoded namespace/environment values inside templates instead of parameterized via `values.yaml` —
  makes the chart usable for exactly one deployment instead of reusable across environments.
- Missing `{{- if }}` guards on optional resources, so an empty/default value renders a broken manifest
  (e.g. an Ingress with no host) instead of omitting the resource cleanly.
- `helm upgrade --install` run directly against production outside of GitOps reconciliation, creating
  drift the GitOps tool will detect and potentially revert unexpectedly.
- Subchart values not properly namespaced under the subchart's key in the parent's `values.yaml`, silently
  not taking effect.
