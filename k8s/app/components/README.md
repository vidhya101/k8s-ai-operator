# `k8s/app/components/` — opt-in Kustomize components

`k8s/app/base/` is already a hardened, HA-by-default workload: startup/liveness/readiness probes,
non-root + `readOnlyRootFilesystem` + dropped capabilities + `RuntimeDefault` seccomp, topology
spread + pod anti-affinity, HPA v2 with tuned behavior, PodDisruptionBudget, default-deny
NetworkPolicy (+ DNS/ingress/egress allows), ResourceQuota, and LimitRange.

These **components** are the pieces that don't belong in every base because they need a
cluster-scoped object or a controller/CRD that may not be installed. A
[Kustomize component](https://kubectl.docs.kubernetes.io/guides/config_management/components/) is
the idiomatic way to make that reusable — pull the ones you want into any overlay:

```yaml
# k8s/app/overlays/<env>/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
components:
  - ../../components/hardening
  - ../../components/vpa
  - ../../components/priority-scheduling
  - ../../components/self-healing
```

Build order note: components are applied **after** `resources`, in listed order, so a component may
patch objects the base defines.

| Component | Adds | Prerequisite (must already be installed) | Safe without prereq? |
|---|---|---|---|
| `hardening` | `Namespace` w/ Pod Security Admission `restricted`; least-privilege `Role` + `RoleBinding` for the app ServiceAccount | none (PSA is built in ≥ 1.25) | yes |
| `vpa` | `VerticalPodAutoscaler` in `Off` (recommender-only) mode | VPA (`autoscaling.k8s.io`) — `vpa-recommender`, `vpa-updater`, `vpa-admission-controller` | **no** — CRD missing → apply fails. See install note in the component. |
| `priority-scheduling` | `PriorityClass` (cluster-scoped); patches the Deployment with `priorityClassName`, an example node-affinity, and a tolerations block | none | yes |
| `self-healing` | Stakater Reloader annotation on the Deployment; Descheduler policy `ConfigMap`; a KEDA `ScaledObject` example (commented); Kyverno guardrail `ClusterPolicy` set (commented) | Reloader / Descheduler / KEDA / Kyverno as you enable each part | partially — the Reloader annotation is a harmless no-op without the controller; the rest is commented until you install its controller |

## Per-cloud

The existing `k8s/app/overlays/{aws,azure,gcp,local}` already patch ingress class, workload-identity
annotations, NetworkPolicy namespace selectors, and node selectors per distro. Add a `components:`
block to whichever overlay(s) you want the add-ons in — they compose cleanly with the cloud patches.

## Verifying a component landed

```bash
kustomize build k8s/app/overlays/<env> | kubectl diff -f -   # preview, no changes
kustomize build k8s/app/overlays/<env> | kubectl apply --dry-run=server -f -
```
