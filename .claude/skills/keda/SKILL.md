---
name: keda
description: KEDA — Kubernetes event-driven autoscaling on queue depth, stream lag, or any external metric, not just CPU/memory. Use alongside kubernetes-autoscaling when HPA's built-in metrics (CPU/memory) don't reflect real load (queue-backed workers, Kafka consumers, cron-like bursts).
---

# KEDA (Kubernetes Event-Driven Autoscaling)

Extends HPA to scale on external event sources — queue depth, Kafka consumer lag, a cron schedule, or
practically any metric with a KEDA scaler — instead of being limited to CPU/memory. See
`kubernetes-autoscaling` for the HPA/VPA/Cluster-Autoscaler fundamentals KEDA builds on top of.

## Core Model

- KEDA installs a `ScaledObject` (or `ScaledJob` for one-shot/batch-style workloads) that wraps a
  standard Kubernetes HPA under the hood — KEDA computes the external metric and feeds it to HPA, rather
  than replacing HPA's mechanics.
- **Scale to zero**: unlike CPU-based HPA (which has a practical floor around 1 replica), KEDA can scale a
  deployment to zero replicas when there's no work queued, and back up when work arrives — the
  Kubernetes-native equivalent of `kserve`'s scale-to-zero, generalized to any event-driven workload, not
  just model serving.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: { name: worker-scaler }
spec:
  scaleTargetRef: { name: queue-worker }
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
        queueLength: "5"          # target ~5 messages per replica
```

## Common Scalers

- **Queue-based** (SQS, RabbitMQ, Azure Service Bus): scale worker replicas to match queue depth —
  directly solves the classic "queue backs up because nothing scaled with it" problem.
- **Kafka**: scale a consumer group's replicas based on consumer lag (see `kafka` skill) — caps out at
  the topic's partition count, same ceiling `kafka` describes for consumer parallelism.
- **Cron**: scale up ahead of a known traffic pattern (e.g. business-hours scale-up, overnight scale-down)
  — a declarative alternative to a separate scheduled job that patches replica counts.
- **Prometheus**: scale on any PromQL query result — the general-purpose escape hatch when no dedicated
  scaler exists for a given metric source.

## Common Pitfalls

- `minReplicaCount: 0` used for a workload with meaningful cold-start latency and no tolerance for it —
  same tradeoff `kserve`'s scale-to-zero section warns about; know the cost before enabling it.
- Scaling target (`queueLength`) not tuned against actual per-replica processing capacity, causing
  over- or under-scaling relative to real throughput.
- A queue-based scaler with no cap (`maxReplicaCount` too high or unset) during a genuine backlog event,
  scaling out far beyond what downstream dependencies (a database, a rate-limited API) can actually absorb
  — the autoscaler solving the queue problem while creating a new bottleneck one layer down.
- KEDA installed cluster-wide but the specific trigger type's required credentials (e.g. AWS IAM for the
  SQS scaler) not configured, so the `ScaledObject` exists but silently never scales past its minimum.
