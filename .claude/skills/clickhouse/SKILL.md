---
name: clickhouse
description: ClickHouse — columnar OLAP database for high-throughput analytical queries over large datasets. Use for analytical/reporting query performance work, distinct from OLTP databases (mysql/postgresql) or the lakehouse/warehouse skills for federated/managed analytics.
---

# ClickHouse

Columnar, OLAP-oriented database built for fast aggregation over huge datasets (billions of rows) —
fundamentally different access pattern from OLTP databases (`mysql`/`postgresql`): optimized for
"aggregate this column across a huge table" rather than "fetch/update one row by primary key fast."

## Why Columnar Changes the Performance Profile

- Data stored column-by-column, not row-by-row — a query aggregating one or two columns across billions
  of rows only reads those columns' data, not entire rows; the same principle `data-lakehouse`'s
  Parquet/Iceberg discussion describes for the lakehouse world, ClickHouse implements natively as a
  database engine rather than a file format read by an external engine.
- This makes ClickHouse excellent at `SELECT metric, COUNT(*) FROM huge_table WHERE ... GROUP BY metric`-
  shaped queries and comparatively poor at single-row lookups/updates or highly transactional workloads —
  it is not a replacement for an OLTP database, and forcing OLTP-shaped access patterns onto it performs
  badly.

## Table Engines & Ordering Key

```sql
CREATE TABLE events (
    event_time DateTime,
    user_id UInt64,
    event_type String,
    value Float64
) ENGINE = MergeTree()
ORDER BY (event_type, event_time)          -- the primary sort/index — queries filtering on a prefix
PARTITION BY toYYYYMM(event_time);         -- of this key are fast; queries on unrelated columns scan more
```

- The `MergeTree` family (and variants like `ReplacingMergeTree` for dedup, `SummingMergeTree` for
  pre-aggregation) is the standard engine choice — the **ordering key** functions like a clustered index:
  design it around the actual filter/aggregation columns the workload uses most, the same
  "access-patterns-first" discipline as `dynamodb`/`cassandra`, applied to column/sort-order choice
  instead of partition key choice.
- Partitioning (commonly by date) enables efficient partition pruning and easy old-data expiry (`DROP
  PARTITION` is a fast metadata operation, unlike a `DELETE` scanning matching rows).

## Common Use Cases

- Real-time analytics dashboards, observability/metrics backends at very high cardinality/volume, event
  analytics — anywhere the query shape is "aggregate over a lot of data" rather than "look up one record."

## Common Pitfalls

- Frequent single-row `INSERT`s or `UPDATE`/`DELETE`-heavy workloads — ClickHouse is optimized for large
  batch inserts, not high-frequency small writes; batch writes application-side before inserting.
- Ordering key chosen without matching actual query filter patterns, forcing full-column scans for
  queries that a well-chosen `ORDER BY`/partition scheme would have made fast.
- Treating it as a general-purpose OLTP replacement — transactional guarantees and row-level update
  performance are not what it's designed for; keep transactional workloads on `mysql`/`postgresql`.
- No `PARTITION BY` on a large time-series table, making old-data expiry an expensive row-scanning
  `DELETE` instead of a cheap partition drop.
