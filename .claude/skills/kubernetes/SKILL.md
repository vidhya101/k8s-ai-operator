---
name: kubernetes
description: Core Kubernetes object design, troubleshooting, and cluster-agnostic operations — Deployments, Services, probes, resource limits, RBAC, NetworkPolicies. Use for any K8s manifest/workload question; use eks/aks/gke/kubeadm/openshift for platform-specific concerns.
---

# Kubernetes (Core)

Distro-agnostic Kubernetes reference. Pair with the specific platform skill (`eks`, `aks`, `gke`,
`kubeadm`, `openshift`) once the cluster's distro is known — don't write generic YAML and assume it
behaves identically everywhere (OpenShift's SCCs and EKS's IRSA are the most common surprises).

## Core Principles

- Every workload gets resource `requests` and `limits` — no unbounded pods.
- Every Deployment gets liveness, readiness, and (for slow-starting apps) startup probes.
- RBAC scoped per namespace/ServiceAccount — no workload runs with `cluster-admin`.
- NetworkPolicies default-deny with explicit allow rules, not open-by-default, once a CNI that enforces
  them is in place (verify the CNI supports NetworkPolicy — not all do out of the box).
- Never `kubectl apply`/`delete`/`edit` directly against a cluster that's GitOps-managed (see `gitops`
  skill) — that creates drift ArgoCD will either fight or silently revert.

## Key Commands (read-only investigation first)

```bash
kubectl config current-context                       # confirm target before anything else
kubectl get <resource> -n <ns> -o wide
kubectl describe <resource> <name> -n <ns>
kubectl logs <pod> -n <ns> [-c <container>] [--previous]
kubectl get events -n <ns> --sort-by=.lastTimestamp
kubectl top pod -n <ns>                               # requires metrics-server
kubectl explain <resource>.<field>                    # schema reference without leaving the terminal
kubectl auth can-i <verb> <resource> -n <ns>          # RBAC check
```

## Storage, Config, and Stateful Workloads

- **ConfigMap/Secret**: decouple config from the image; mounted as env vars (read once, at container
  start — a ConfigMap edit does *not* update already-injected env vars) or as a volume (kubelet syncs
  updated content into the mounted files, but the application still needs to watch/reload them — nothing
  restarts the process automatically). Know which propagation model a workload actually relies on before
  assuming "I edited the ConfigMap" was enough.
- **PersistentVolume/PersistentVolumeClaim/StorageClass**: a `PVC` requests storage matching a
  `StorageClass`'s provisioner (dynamic provisioning is the default on every major cloud/CSI driver
  today); the `PV` is the bound, concrete unit of storage. `accessModes` (`ReadWriteOnce`,
  `ReadWriteMany`, `ReadOnlyMany`) must match what the storage backend actually supports — requesting
  `ReadWriteMany` on a backend that only supports `ReadWriteOnce` (most block storage) fails to bind.
- **StatefulSet**: for workloads needing stable network identity (predictable pod names/DNS:
  `<pod>.<service>.<namespace>.svc.cluster.local`) and/or stable per-replica storage
  (`volumeClaimTemplates`, one PVC per pod that survives pod rescheduling). Pods are created/scaled/
  updated in ordinal order (0, 1, 2, ...) by default — this ordering is what makes StatefulSets suitable
  for clustered stateful software (databases, brokers) that cares about join order, at the cost of slower
  rollouts than a Deployment's parallel pod replacement.
- **Internal DNS**: CoreDNS resolves `<service>.<namespace>.svc.cluster.local` (often reachable within
  the same namespace as just `<service>`) — a `Service` gets a stable DNS name regardless of which pods
  back it; a `StatefulSet`'s headless Service additionally gives each pod its own stable DNS record. A
  `CrashLoopBackOff`-free pod that still can't reach another service by name is very often a namespace
  mismatch in the hostname, not a networking failure.

## Workload Design Checklist

1. `requests`/`limits` set and realistic (limits too tight cause throttling/OOMKill; too loose defeats
   scheduling and bin-packing).
2. Probes: readiness gates traffic, liveness restarts a genuinely stuck process — don't make liveness so
   aggressive it restarts a pod that's just slow under load (that compounds an incident).
3. `PodDisruptionBudget` on anything needing availability through voluntary disruption (node drain, cluster
   upgrade).
4. Anti-affinity or topology spread constraints across nodes/zones for anything requiring HA.
5. Secrets mounted (env or volume) from the platform's secret manager integration, not raw `Secret`
   manifests with plaintext committed to git.
6. ConfigMap/Secret changes: know whether the workload picks them up automatically (mounted volume + app
   watches for changes) or needs a rollout to pick up new values.

## Common Pitfalls

- Liveness probe hitting the same endpoint/timeout as readiness, so a slow-but-recovering pod gets killed
  instead of just pulled from the Service.
- `emptyDir` used for data that needs to survive pod restart — should be a `PersistentVolumeClaim`.
- A Service selector that doesn't match the Deployment's pod labels after a label change — silent routing
  failure with no error, only symptoms.
- Namespace-wide `RoleBinding` to a broad group when a specific ServiceAccount binding would do.
