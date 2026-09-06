---
name: kubecost
description: Kubecost — Kubernetes-native cost visibility and allocation, breaking cloud spend down by namespace/deployment/team/label. Use for Kubernetes-specific cost attribution, complementing the principal-finops-engineer agent's broader cloud cost governance lens.
---

# Kubecost

Solves the specific cost-attribution gap a cloud bill alone can't: a cloud invoice shows what the whole
EKS/AKS/GKE cluster cost, but not which namespace, team, or deployment actually drove that spend. See the
`principal-finops-engineer` agent for the broader cost-governance discipline this feeds into.

## Core Capability

- Allocates cluster cost (compute, memory, storage, network, and cloud-provider list prices for the
  underlying nodes) down to namespace/deployment/label/team granularity — turns "our EKS cluster costs
  $40k/month" into "team X's namespace accounts for $12k of that, mostly from three oversized deployments."
- Tracks **idle cost**: capacity provisioned (requested, or node capacity reserved) but not actually used
  — directly actionable rightsizing data, the concrete input the `principal-finops-engineer` agent's
  rightsizing checklist needs rather than a vague utilization guess.

```bash
kubectl cost namespace --window 7d                      # cost by namespace over the last week
kubectl cost deployment --namespace my-ns --window 30d    # cost by deployment within a namespace
```

## Efficiency Metrics

- **Request vs. usage**: compares what a workload *requested* (which is what actually drives bin-packing
  and, for provisioned capacity, cost) against what it *used* — the direct evidence for a rightsizing
  recommendation, rather than eyeballing `kubectl top` output.
- Cluster-level efficiency (total requested vs. total node capacity) surfaces whether the cluster overall
  is oversized for its workloads, independent of any single workload's efficiency — a different, higher-
  level signal than per-workload rightsizing.

## Common Pitfalls

- Cost data reviewed once during an initial audit and never checked again — cost attribution drifts as
  fast as the workloads themselves change; this needs to be an ongoing input to capacity decisions, not a
  one-time report.
- Namespace/label conventions inconsistent across teams, making cost-by-team rollups unreliable — Kubecost
  can only attribute cost as precisely as the underlying labeling discipline allows (same "cost allocation
  needs tagging discipline" principle the `aws`/`azure`/`gcp` skills describe, applied at the K8s layer).
- Rightsizing recommendations acted on without checking for legitimate headroom needs (burst capacity,
  planned growth) — same caution the `principal-finops-engineer` agent applies generally: a cost fix that
  removes needed headroom isn't a clean win, it's a trade-off to make deliberately.
- Idle cost data available but never actually reviewed/acted on — visibility without a process to act on
  it doesn't save anything by itself.
