---
name: cassandra
description: Apache Cassandra — wide-column NoSQL with tunable consistency, distinct from DynamoDB's fully-managed model and MongoDB's document model. Use for Cassandra-specific data modeling, consistency-level tuning, or cluster troubleshooting.
---

# Cassandra

Distributed wide-column store designed for write-heavy, always-available workloads across multiple
data centers — the self-managed/open-source counterpart to the data-modeling discipline `dynamodb`
describes (access-patterns-first schema design), with its own specific consistency and topology model.

## Data Modeling: Same "Access Patterns First" Discipline as DynamoDB

- Cassandra tables are designed around **query patterns**, not normalized entities — denormalization
  (the same data duplicated across multiple tables, each shaped for a specific query) is standard
  practice, not a smell, exactly as in `dynamodb`'s single-table-design discussion.
- **Partition key** determines data distribution (same hot-partition risk as DynamoDB's partition key —
  low cardinality or skewed access causes hot nodes); **clustering columns** determine on-disk sort order
  within a partition, enabling efficient range queries within one partition.

## Tunable Consistency

- Cassandra lets each read/write specify a **consistency level** (`ONE`, `QUORUM`, `ALL`, etc.) — how
  many replicas must acknowledge before the operation is considered successful. This is Cassandra's
  version of the durability-vs-latency tradeoff every distributed system has (`kafka`'s `acks`,
  `database-operations`' sync-vs-async replication) — `QUORUM` writes + `QUORUM` reads gives strong
  consistency (guaranteed to see the latest write), `ONE` gives lower latency but can read stale data.
- **Eventual consistency** is the default assumption for anything not using `QUORUM`+ on both reads and
  writes — application logic needs to be written with that in mind, the same idempotency/staleness-
  tolerance discipline as any eventually-consistent system.

## Cluster Topology

- **Replication factor** (per keyspace) and **multi-datacenter replication** (`NetworkTopologyStrategy`)
  are how Cassandra achieves multi-region availability — a keyspace using `SimpleStrategy` doesn't
  meaningfully support multi-DC deployments; check which strategy is actually configured before assuming
  cross-region resilience.
- **Repair** (`nodetool repair`) reconciles replicas that have drifted due to missed writes (a node down
  during a write, then recovering) — needs to run periodically (Cassandra doesn't do this automatically
  by default in most setups); skipped repairs accumulate inconsistency that eventual consistency alone
  won't naturally resolve past the hinted-handoff window.

```bash
nodetool status                  # cluster/node health, ownership distribution
nodetool describecluster
nodetool repair -pr               # incremental repair, scoped per node
```

## Common Pitfalls

- A partition key that doesn't distribute evenly (e.g. a low-cardinality status field), creating a hot
  partition the same way a poor DynamoDB partition key choice does.
- Consistency level chosen without matching the actual requirement — `ONE` used where strong consistency
  was actually needed, silently allowing stale reads.
- Repairs never scheduled, letting replica drift accumulate past the point normal read-repair/hinted
  handoff can quietly fix it, discovered only when a node replacement or major failure surfaces the gap.
- Modeling Cassandra relationally (joins, secondary indexes as a crutch for normalized design) instead of
  denormalizing around actual query patterns — the identical anti-pattern `dynamodb` warns against.
