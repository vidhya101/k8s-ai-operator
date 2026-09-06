---
name: cloud-data-warehouse
description: Managed cloud data warehouses — Snowflake, BigQuery, Redshift — cost/query-optimization model and where they fit versus a lakehouse. Use for warehouse schema/cost design, distinct from data-lakehouse's Spark-over-open-table-formats approach or aws-data-analytics's Athena/Glue.
---

# Cloud Data Warehouses (Snowflake, BigQuery, Redshift)

Fully-managed, SQL-first analytical stores — distinct from `data-lakehouse` (Spark compute over
open-format files you own in your own storage) and `aws-data-analytics`'s Athena (serverless SQL directly
over S3). A warehouse trades some of the lakehouse's storage-format openness/portability for a more
polished, fully-managed query/optimization experience.

## Cost Model Differences (the thing that most affects design)

- **Snowflake**: separates storage cost from compute cost — compute runs in independently-sizable
  "warehouses" (confusingly named the same as the platform) that can auto-suspend when idle; cost is
  driven by compute-seconds actually used, not data scanned per query the way Athena/BigQuery on-demand
  billing works.
- **BigQuery**: on-demand pricing bills per byte scanned per query (same cost lever as Athena — partition
  pruning and column selection directly control cost) or flat-rate/capacity-based pricing for predictable
  high-volume workloads — know which billing mode a project is on before assuming query cost behavior.
- **Redshift**: provisioned-cluster pricing (pay for cluster uptime regardless of query volume) or
  Redshift Serverless (pay per query, closer to BigQuery/Athena's model) — the provisioned model rewards
  keeping the cluster busy, unlike the pay-per-query models which reward query efficiency specifically.

## Common Optimization Levers

- **Partition/cluster pruning**: partitioning (BigQuery/Redshift) or clustering keys (Snowflake's
  micro-partitions, automatic but influenceable) that match actual filter columns — same principle as
  `data-lakehouse`'s partition strategy, expressed through each platform's own mechanism.
- **Materialized views**: pre-compute expensive, frequently-repeated aggregations — trades storage/
  refresh cost for query-time savings; worth it for a dashboard query pattern hit constantly, not for a
  one-off analysis.
- **Result caching**: most platforms cache identical repeated queries automatically — relevant when
  benchmarking/comparing query performance (a "fast" second run may just be a cache hit, not a real
  optimization win).

## Common Pitfalls

- `SELECT *` (or scanning far more columns/partitions than needed) on a per-byte-billed platform
  (BigQuery on-demand, Athena) — directly and often substantially inflates cost, the same warning
  `aws-data-analytics` gives for Athena, applying identically here.
- Snowflake warehouse left running (not auto-suspending) between queries, burning compute cost on idle
  time — check `AUTO_SUSPEND` is set to something sensible for the workload's actual query cadence.
- Redshift provisioned cluster sized for peak load and left running at that size continuously instead of
  using Redshift Serverless or scheduled resize for a workload that's actually bursty — same
  right-sizing principle the `principal-finops-engineer` agent applies generally.
- Treating the warehouse as a place to also run heavy ETL/transformation logic that would be cheaper/more
  appropriate in a lakehouse compute engine (`data-lakehouse`) or orchestrated pipeline (`airflow`) — a
  warehouse's compute is usually the most expensive place to do that work per unit of compute.
