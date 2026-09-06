---
name: kafka
description: Apache Kafka (including AWS MSK) — topics/partitions, consumer groups, and delivery semantics. Use for streaming/event-backbone design or troubleshooting, whether self-managed, MSK, or another managed Kafka offering.
---

# Kafka (including MSK)

Distributed log-based streaming platform — the durable, replayable backbone for event-driven
architectures at higher throughput/retention than a queue like SQS is designed for. MSK is AWS's managed
Kafka offering; the concepts below are Kafka-native and apply whether self-managed, MSK, Confluent Cloud,
or another provider.

## Core Concepts

- **Topic**: a named stream of records, split into **partitions** for parallelism — partition count sets
  the ceiling on consumer parallelism (one partition is consumed by at most one consumer within a
  consumer group at a time), and is difficult to reduce later (only increasable) — under-provisioning
  partitions is a common early mistake that's costly to fix once producers/consumers depend on the
  existing partitioning scheme.
- **Consumer group**: a set of consumers sharing the work of consuming a topic — Kafka tracks each
  group's committed offset per partition, which is what makes "resume where we left off after a restart"
  work without external bookkeeping.
- **Replication factor**: how many broker copies of each partition exist — determines fault tolerance
  (replication factor 3 tolerates 2 broker failures); `min.insync.replicas` combined with producer
  `acks=all` is what actually controls durability guarantees, not replication factor alone.
- **Retention**: time- or size-based (`retention.ms`/`retention.bytes`), or log-compacted (keeps only the
  latest value per key, for topics representing current state rather than an event history) — pick based
  on whether consumers need the full event history or just the latest state per key.

## Delivery Semantics

- **At-most-once**: commit offset before processing — risk of losing messages on a crash between commit
  and processing completion.
- **At-least-once** (most common default): commit offset after processing — risk of reprocessing on a
  crash between processing and commit; consumers must be idempotent to handle this safely (same
  discipline as `data-engineering-reviewer`'s core principle, applied to streaming).
- **Exactly-once**: achievable within Kafka-to-Kafka pipelines via Kafka's transactional producer/consumer
  API — more complex to implement correctly and has throughput cost; confirm it's actually required before
  taking on that complexity versus idempotent at-least-once consumption.

## Operational Basics

```bash
kafka-topics.sh --bootstrap-server <broker> --describe --topic <topic>
kafka-consumer-groups.sh --bootstrap-server <broker> --describe --group <group>   # consumer lag per partition
kafka-console-consumer.sh --bootstrap-server <broker> --topic <topic> --from-beginning
```

- **Consumer lag** (difference between the latest produced offset and a group's committed offset) is the
  primary health signal — growing, unbounded lag means consumers can't keep up with production rate;
  monitor it as a first-class metric (exportable to Prometheus via a JMX exporter or MSK's own CloudWatch
  metrics), not an afterthought.

## Schema Registry

- Enforces a shared, versioned schema (Avro/Protobuf/JSON Schema) for a topic's messages — without it,
  producers and consumers rely on informal agreement about message shape, which breaks silently the
  moment one side changes without the other knowing.
- **Compatibility modes** (`BACKWARD`, `FORWARD`, `FULL`, or `NONE`) control what schema changes are
  allowed: `BACKWARD` compatible means new schema can read old data (safe to upgrade consumers first),
  `FORWARD` means old schema can read new data (safe to upgrade producers first) — picking the wrong mode
  for the actual deployment order is a common source of a "compatible" schema change still breaking
  production during a rolling deploy.
- Treat a schema registry the same as an API contract (`contract-testing` skill's discipline) — a
  breaking schema change needs the same coordination as a breaking API change, not a silent topic-level
  surprise for consumers.

## Consumer Lag Troubleshooting

```bash
kafka-consumer-groups.sh --bootstrap-server <broker> --describe --group <group>
```

Growing, sustained lag has a small number of usual causes, worth checking in order:

1. **Slow consumer processing** — the consumer's per-message work (a slow downstream call, an expensive
   transform) takes longer than the production rate requires; check consumer-side processing time, not
   just Kafka-side metrics.
2. **Under-partitioned topic relative to needed parallelism** — see the Core Concepts section; a
   partition count ceiling on consumer group size that's already maxed out.
3. **Rebalancing thrash** — frequent consumer group rebalances (from consumers joining/leaving, or
   session timeouts too aggressive for actual processing time) pause consumption during each rebalance;
   check rebalance frequency in consumer logs before assuming raw throughput is the issue.
4. **A stuck/crashed consumer instance** not actually processing but not visibly failed either — verify
   every expected consumer instance in the group is actually alive and making progress, not just that the
   group exists.

## MSK-Specific Notes

- Broker sizing/count and storage autoscaling are managed but still require capacity planning — same
  discipline as any AWS-managed data service (see `aws` skill's cost/quota governance principle).
- IAM authentication (as an alternative to SASL/SCRAM or mTLS) is MSK-specific and simplifies credential
  management by tying producer/consumer access to IAM policies — check which auth mode a given MSK
  cluster uses before assuming a generic Kafka client config will connect.

## Common Pitfalls

- Under-provisioned partition count discovered only once consumer parallelism needs exceed it, requiring
  a disruptive migration (partition count changes break key-based ordering guarantees for existing keys).
- Consumers not idempotent, so the default at-least-once delivery causes duplicate processing on any
  rebalance/restart — a correctness bug, not just an edge case, since rebalances happen routinely.
- No consumer lag monitoring/alerting, so a stuck or slow consumer group is discovered only when
  downstream data is already significantly stale.
- `acks=1` (leader-only acknowledgment) used for data where durability actually matters — a leader
  failure right after acknowledging can lose the message; `acks=all` with appropriate
  `min.insync.replicas` is needed for real durability guarantees.
