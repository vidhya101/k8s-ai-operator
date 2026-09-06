---
name: kubernetes-autoscaling
description: Kubernetes autoscaling end to end — metrics-server, HPA, VPA, and Cluster Autoscaler/Karpenter. Use when configuring or debugging why a workload or the cluster itself isn't scaling as expected.
---

# Kubernetes Autoscaling (metrics-server, HPA, VPA, Cluster Autoscaler)

Four layers that depend on each other in a specific order — a scaling problem is very often actually a
problem one layer down, not the layer where the symptom shows up.

```text
metrics-server  → HPA / VPA read from it   → pods scale (or don't)
                                            → if pods can't schedule (insufficient node capacity),
Cluster Autoscaler / Karpenter reacts to unschedulable pods → adds nodes
```

## metrics-server

- Cluster-wide component that collects CPU/memory usage from kubelets and exposes it via the Kubernetes
  Metrics API — both `kubectl top` and HPA (for CPU/memory-based scaling) depend on it being installed
  and healthy. No metrics-server means HPA can't function for resource-based metrics at all, not degraded
  — completely nonfunctional, and the failure mode is often just "HPA never scales, no clear error."

```bash
kubectl get deployment metrics-server -n kube-system
kubectl top nodes / kubectl top pods -n <ns>     # fails immediately if metrics-server is down/missing
```

## HPA (Horizontal Pod Autoscaler)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: my-app }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: my-app }
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

- Requires `resources.requests` set on the target workload — utilization percentage is calculated against
  the request, not the limit; a workload with no CPU request can't be scaled on CPU utilization.
- Can scale on custom/external metrics (via a metrics adapter, e.g. Prometheus Adapter) instead of just
  CPU/memory — useful for scaling on queue depth, request rate, or another business-relevant signal.

## VPA (Vertical Pod Autoscaler)

- Adjusts a pod's resource requests/limits over time based on observed usage, instead of (or alongside)
  changing replica count. `updateMode: "Auto"` evicts and recreates pods to apply new sizing — causes
  disruption, so know whether that's acceptable for the workload before enabling it; `"Off"` mode only
  recommends without applying, useful for right-sizing research without any live disruption.
- **VPA and HPA scaling on the same metric (CPU/memory) conflict** — VPA changing the request while HPA
  calculates utilization against that same request creates a feedback loop. If both are needed on one
  workload, scale HPA on a different metric than the one VPA is adjusting.

## Cluster Autoscaler / Karpenter (node-level scaling)

- Reacts to **unschedulable pods** (not to raw resource utilization) — adds nodes when pods are `Pending`
  due to insufficient capacity, removes nodes that are underutilized and whose pods could be rescheduled
  elsewhere. See `eks`/`aks`/`gke`/`kubeadm` skills for the platform-specific mechanism (Karpenter is
  AWS-originated but has broader adoption; Cluster Autoscaler is the more universal/portable option).
- A pod stuck `Pending` with no new node appearing usually means: no node group/pool configured to satisfy
  its requested resources/labels/taints-tolerations, or the autoscaler has hit its configured max node
  count — check both before assuming the autoscaler itself is broken.

## Karpenter Specifics

- Unlike the traditional Cluster Autoscaler (which scales pre-defined node groups up/down), Karpenter
  provisions nodes directly matching what unschedulable pods actually need — picks instance type/size/AZ
  dynamically per the pending pods' requirements, rather than scaling a fixed-shape node group.
  Consequence: faster provisioning and better bin-packing, but node shapes are less predictable, which
  matters if something downstream (monitoring, cost allocation) assumed fixed, known node types.
- Consolidation (Karpenter can proactively replace/reschedule pods onto fewer, better-packed nodes even
  without new unschedulable pods triggering it) is a distinct behavior from Cluster Autoscaler's more
  conservative scale-down — worth knowing when nodes seem to churn "on their own" outside an obvious
  scaling event.

## KEDA for Event-Driven Workloads

For workloads that should scale on something other than CPU/memory (queue depth, Kafka lag, a cron
schedule) — see the dedicated `keda` skill. The short version: KEDA wraps HPA to feed it external metrics,
so it composes with the HPA discussion above rather than replacing it, and uniquely supports true
scale-to-zero, which plain CPU/memory-based HPA cannot do.

## Common Pitfalls

- HPA configured on a Deployment with no resource `requests` set — utilization can't be computed, HPA
  effectively does nothing, often with no obvious error surfaced to a quick glance at the HPA object.
- VPA in `Auto` mode on a workload that can't tolerate pod recreation disruption (no PodDisruptionBudget,
  no readiness gating) — the "autoscaling" itself becomes a source of availability issues.
- HPA and VPA both targeting CPU on the same workload, causing oscillation as each reacts to the other's
  changes.
- Cluster Autoscaler/Karpenter's max node count left at a default that's lower than genuine peak need,
  silently capping scale-out during a real traffic spike.
