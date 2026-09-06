---
name: dynamodb
description: Amazon DynamoDB — partition key design, capacity modes, GSIs/LSIs, and single-table design. Use for DynamoDB-specific schema/access-pattern questions; see database-operations for cross-database backup/DR principles that still apply.
---

# DynamoDB

AWS-native NoSQL key-value/document store — fundamentally different design discipline from relational
databases (`mysql`/`postgresql`) or MongoDB's flexible-document model: DynamoDB requires designing the
schema around known access patterns *up front*, not evolving it organically.

## Partition Key Design

- The partition key determines how data distributes across DynamoDB's underlying storage partitions —
  low-cardinality or unevenly-accessed partition keys create **hot partitions**, which throttle that
  specific partition's throughput regardless of the table's overall provisioned/on-demand capacity. This
  is the single most consequential design decision and, like a Kafka topic's partition count, is
  expensive to fix after data and access patterns are already built around it.
- A composite key (partition key + sort key) enables range queries and hierarchical data modeling within
  one partition (e.g. partition key `customerId`, sort key `orderDate#orderId` for "all orders for a
  customer, sorted by date").

## Access Patterns Drive Schema (Single-Table Design)

- Unlike a relational schema (design tables, then write queries), DynamoDB schema design starts from
  **enumerating every access pattern the application needs**, then designing keys/indexes to serve them —
  designing the table first and figuring out queries later is the most common source of an unworkable
  DynamoDB schema.
- **Single-table design** (multiple entity types in one table, distinguished by key prefixes/patterns)
  is the common advanced pattern for serving many access patterns with few requests — powerful but adds
  real complexity; a simple application with few access patterns doesn't need to reach for it (Section 1.2).

## Capacity Modes

- **On-demand**: pay per request, no capacity planning, scales automatically — good default for
  unpredictable/spiky traffic or when starting out.
- **Provisioned** (with optional auto-scaling): cheaper at steady, predictable high throughput, but under-
  provisioning causes throttling (`ProvisionedThroughputExceededException`) — same capacity-planning
  discipline as any other capacity-based resource.

## Indexes

- **GSI (Global Secondary Index)**: a different partition/sort key than the base table, its own
  provisioned/on-demand capacity, eventually consistent — needed to support a query pattern the base
  table's key structure doesn't serve directly.
- **LSI (Local Secondary Index)**: same partition key as the base table, different sort key, must be
  created at table creation time (cannot be added later) — a much more constrained tool than a GSI;
  confirm it's genuinely needed before committing to it, since a missing access pattern later can't be
  retrofitted as an LSI.

## Common Pitfalls

- A partition key with low cardinality (e.g. a status field with 3 possible values) as the sole
  partition key, causing severe hot-partitioning under real load.
- Schema designed relationally-first (normalized tables, join-like patterns) then forced into DynamoDB,
  producing either N+1-style multiple round trips or an unworkable design — DynamoDB rewards
  denormalization for the access patterns that matter.
- On-demand capacity assumed to have zero limits — it still has account/table-level throughput ceilings
  and can throttle under a sudden, extreme spike beyond its scaling rate.
- No point-in-time recovery (PITR) enabled — the DynamoDB-specific form of the `database-operations`
  skill's "verify backups are actually restorable" principle; PITR must be explicitly enabled per table.
