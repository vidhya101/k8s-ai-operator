---
name: data-lakehouse
description: Lakehouse architecture — distributed compute with Spark/Databricks over open table formats (Iceberg, Delta Lake). Use for large-scale batch/streaming data processing design, or reviewing a Spark job/table-format choice; pair with airflow for orchestration and database-operations for general data-reliability principles.
---

# Data Lakehouse (Spark/Databricks + Iceberg/Delta Lake)

Combines data-lake storage economics (cheap object storage, open formats) with data-warehouse-like
transactional guarantees (ACID, schema evolution, time travel) — the processing engine (Spark/Databricks)
and the table format (Iceberg/Delta Lake) are two halves of the same architecture, addressed together
here. See `airflow` for orchestrating these jobs and `database-operations` for reliability principles
(backup/migration discipline) that still apply to lakehouse tables.

## Distributed Compute: Spark / Databricks

- Spark distributes a transformation across a cluster by partitioning data — job performance is
  dominated by partition sizing (too many small partitions = scheduling overhead; too few large ones =
  poor parallelism/skew) and by minimizing shuffles (expensive cross-partition data movement, typically
  triggered by joins/aggregations/repartitioning).
- **Data skew** (one partition far larger than others due to uneven key distribution) is the most common
  cause of a Spark job where "everything finished except one straggler task" — salting the skewed key or
  using a skew-aware join strategy are the standard fixes.
- Databricks adds a managed runtime, notebooks, job scheduling, and Unity Catalog (governance/lineage) on
  top of open-source Spark — check whether a project is on managed Databricks or self-managed Spark
  (EMR, Dataproc, self-hosted on Kubernetes) before assuming Databricks-specific features are available.

```python
df = spark.read.format("iceberg").load("catalog.db.table")
df.groupBy("key").count().write.mode("overwrite").saveAsTable("catalog.db.result")
```

## Table Formats: Iceberg / Delta Lake

- Both provide ACID transactions, schema evolution (add/rename/drop columns without rewriting the whole
  table), time travel (query a table as of a previous snapshot/version), and partition evolution
  (Iceberg) — solving the classic data-lake problems of no transactional guarantees and painful schema
  changes on raw Parquet/ORC files.
- **Iceberg**: engine-agnostic (Spark, Flink, Trino, Snowflake all support it), increasingly the
  cross-vendor standard; **Delta Lake**: originated with and most deeply integrated into Databricks,
  though also usable elsewhere via Delta Lake's open-source connectors.
- Compaction/optimization (merging many small files produced by frequent writes into fewer larger ones)
  is not automatic by default in all setups — check whether it's scheduled; an un-compacted table with
  thousands of small files degrades query performance significantly over time.

```sql
-- Time travel (syntax varies slightly by format/engine):
SELECT * FROM catalog.db.table VERSION AS OF 12345;
SELECT * FROM catalog.db.table TIMESTAMP AS OF '2024-01-01';

-- Schema evolution:
ALTER TABLE catalog.db.table ADD COLUMN new_field STRING;
```

## Common Pitfalls

- Small-file accumulation from frequent incremental writes with no scheduled compaction — the single most
  common lakehouse performance-degradation cause, and easy to not notice until queries have already
  slowed significantly.
- Data skew silently making one Spark task the bottleneck for an entire job, misread as "the cluster needs
  more resources" when the actual fix is addressing the skewed key.
- Schema evolution used to paper over an upstream data-quality issue instead of fixing the source — a
  lakehouse's schema flexibility makes it easy to silently accept malformed/unexpected data.
- Partition strategy chosen without matching actual query filter patterns — same principle as a database
  index: a partition column the queries don't actually filter on doesn't help, and can hurt if it creates
  too many small partitions.
