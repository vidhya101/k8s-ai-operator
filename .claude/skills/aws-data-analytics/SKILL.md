---
name: aws-data-analytics
description: AWS data and analytics services — Glue (ETL), Lake Formation, Athena, and EMR. Use when the data pipeline is built on native AWS analytics services rather than (or alongside) self-managed Spark/Airflow; pair with data-lakehouse and airflow for the platform-agnostic concepts.
---

# AWS Data & Analytics (Glue, Lake Formation, Athena, EMR)

AWS-native managed services covering the same lakehouse/ETL territory as `data-lakehouse` (Spark) and
`airflow` (orchestration), but as managed offerings with their own operational specifics.

## Glue

- **Glue Jobs**: managed Spark (or Python Shell for lighter tasks) ETL, billed per DPU-hour — check job
  type (Spark vs. Python Shell vs. Ray) matches the actual workload; using full Spark for a small
  transformation wastes DPU cost that a Python Shell job would avoid.
- **Glue Crawlers**: infer schema from data in S3 and populate the Glue Data Catalog — convenient for
  onboarding new data sources, but crawler-inferred schema can drift from what a consuming query expects
  as source data evolves; a manually-defined/versioned schema is safer for anything business-critical.
- **Glue Data Catalog**: the central metadata store other services (Athena, EMR, Redshift Spectrum) read
  from — a table registered incorrectly here (wrong partition scheme, stale schema) breaks every
  downstream consumer, not just Glue jobs.

## Lake Formation

- Centralizes fine-grained access control (row/column/tag-based) over S3 data lake tables registered in
  the Glue Data Catalog — the AWS-native answer to "who can query which columns/rows of this table,"
  layered on top of (not replacing) the IAM permissions on the underlying S3 objects.
- Migrating an existing S3-based data lake under Lake Formation governance is a deliberate project (schema
  registration, permission migration) — don't assume it's transparently equivalent to raw S3+IAM access.

## Athena

- Serverless SQL query engine directly over S3 data (via the Glue Data Catalog) — billed per data
  scanned, so partitioning and columnar formats (Parquet/ORC, see `data-lakehouse`) directly control cost,
  not just performance; an unpartitioned table scanned by every query is both slow and expensive.
- `MSCK REPAIR TABLE` (or Glue Crawler) needed after new partitions land if using Hive-style partitioning
  and the catalog isn't otherwise kept in sync — a query "missing" recently-arrived data is often a
  partition-registration gap, not a data pipeline failure.

## EMR

- Managed Hadoop/Spark clusters — EMR on EC2 (full cluster control), EMR Serverless (no cluster
  management, pay-per-job), or EMR on EKS (runs on an existing Kubernetes cluster) — pick based on how
  much infrastructure control is actually needed vs. wanting the operational simplicity of serverless.
- Same Spark performance principles apply as in `data-lakehouse` (partition sizing, shuffle minimization,
  data skew) — EMR is a deployment model for Spark, not a different processing engine.

## Common Pitfalls

- Athena queries against an unpartitioned or non-columnar (raw CSV/JSON) table at any real data volume —
  both cost and latency suffer; converting to partitioned Parquet is usually the single highest-leverage
  fix for an expensive Athena workload.
- Glue Crawler re-run on a schedule against evolving data, silently changing the catalog's inferred schema
  in a way that breaks a downstream consumer expecting the old shape.
- Lake Formation permissions configured but the underlying S3 bucket policy/IAM still allows broader
  direct access, undermining the fine-grained control Lake Formation was meant to enforce.
- EMR cluster sized (and left running) for peak load without considering EMR Serverless or scheduled
  scale-down for a workload that's actually bursty/scheduled rather than continuous.
