# `fleet/` — running this on many clusters (the "1,000,000 pods" question)

## The rule

One cluster's supported ceiling is ~5,000 nodes / ~150,000 pods / ~300k total objects (kube.io
scalability thresholds). 1M pods = **a fleet of clusters**, not one big cluster. You never build a
component that reaches into 1M pods from one place. You run the **same small, proven stack in every
cluster** and aggregate the *signals*, never the *control*.

```
                         ┌───────────────────────────────────────────┐
   cluster inventory      │  Git repo: clusters/*.yaml (one per cluster)│
   (source of truth)      └───────────────────────┬───────────────────┘
                                                  │
                    ArgoCD ApplicationSet (git generator / cluster generator)
                                                  │  renders the SAME app N times
        ┌─────────────────────────┬───────────────┼───────────────┬─────────────────────────┐
   cluster-a (EKS)          cluster-b (AKS)   cluster-c (GKE)  cluster-d (kubeadm)   ... cluster-n
   ├ observability stack    ├ same            ├ same           ├ same
   ├ detection (rules)      ├ same            ├ same           ├ same
   ├ prevention (Kyverno)   ├ same            ├ same           ├ same
   ├ remediation controllers├ same            ├ same           ├ same
   └ 1 agent instance       └ 1 agent         └ 1 agent        └ 1 agent
        │ remoteWrite            │                  │                │
        └────────────────────────┴──── central Mimir/Thanos ─────────┘   (signals only)
                                         + global Grafana + global alert rules
                                         + Alertmanager (dedup across clusters)
```

## Config delivery — ArgoCD ApplicationSet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: platform-selfhealing
  namespace: argocd
spec:
  goTemplate: true
  generators:
    - clusters: {}            # every cluster registered to Argo CD, or filter by a label
  template:
    metadata:
      name: 'platform-{{.name}}'
    spec:
      project: platform
      source:
        repoURL: <this repo>
        targetRevision: main
        path: k8s/platform
        # per-cluster overrides (region, storageClass, registry allowlist) via a values file
        # selected by {{.metadata.labels.env}} — kustomize components or helm valueFiles
      destination:
        server: '{{.server}}'
      syncPolicy:
        automated: { prune: true, selfHeal: true }   # GitOps IS a remediation layer: drift is reconciled
        retry: { limit: 5, backoff: { duration: 30s, maxDuration: 5m } }
```

One definition → every cluster gets identical detection/prevention/remediation. Adding a cluster =
one file in `clusters/`. Rolling a policy change to 500 clusters = one PR.

## Agent sharding

- **One `kubernetes-troubleshooter` instance per cluster** (or per shard of ~50k pods). Each holds
  one watch + a rate-limited work queue — reacts in milliseconds, never "scans".
- Instances are **stateless** and identical; the cluster they target is their only config.
- Circuit-breaker counters are **per-cluster** (a storm in cluster-x must not pause cluster-y).
- Results (what was remediated, what was escalated) are written back as Events + to the central
  audit log in Mimir/Loki — that's the only cross-cluster aggregation.
- A **fleet view** is a Grafana dashboard over the central store, not a central controller.

## What stays central vs per-cluster

| Central (signals) | Per-cluster (control) |
|---|---|
| Mimir/Thanos long-term metrics | Prometheus scrape + local 24h retention |
| Global Grafana + dashboards | in-cluster alert evaluation (PrometheusRules) |
| Alertmanager dedup + routing | Kyverno admission enforcement |
| Audit log aggregation | remediation controllers + agent instance |
| Cluster inventory (Git) | node recovery, descheduler, autoscaler |
| ApplicationSet definition | actual `kubectl`/`apply` execution |

If the central store is down, every cluster still detects and self-heals locally — you lose the
fleet *view*, not the fleet's *resilience*. That's the point of the split.
