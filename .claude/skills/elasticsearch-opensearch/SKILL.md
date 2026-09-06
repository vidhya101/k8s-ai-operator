---
name: elasticsearch-opensearch
description: Elasticsearch/OpenSearch — index design, sharding, and cluster health, for full-text search and log analytics workloads. Use for search/log-analytics cluster design or troubleshooting, distinct from Loki's label-indexed log model.
---

# Elasticsearch / OpenSearch

Full-text search and analytics engine, commonly used for search features and (as an alternative to
`loki`) full-text log indexing. OpenSearch is the open-source fork (post Elastic's license change);
concepts below apply to both unless noted.

## Index Design & Sharding

- An **index** is split into **shards** at creation time — shard count is effectively fixed afterward
  (Elasticsearch's "shrink"/"split" APIs exist but are non-trivial operations, not a casual resize) — the
  same "get this right up front" caution as a Kafka topic's partition count or a DynamoDB table's
  partition key.
- Over-sharding (too many small shards) wastes cluster overhead (each shard has real memory/CPU cost
  regardless of size); under-sharding limits parallelism and caps how large an index can grow — size
  shards against expected data volume, not a default guess.
- **Index Lifecycle Management (ILM)** / Index State Management (OpenSearch) automates the hot→warm→cold→
  delete progression for time-series indices (daily log indices, etc.) — without it, old indices
  accumulate indefinitely on expensive "hot" storage tier.

## Mapping

- Field types are inferred automatically ("dynamic mapping") unless explicitly defined — convenient for
  getting started, risky for anything production: an unexpected field type (a numeric field that
  sometimes arrives as a string) can cause mapping conflicts that reject subsequent documents. Explicit
  mappings for anything beyond exploratory use are worth the upfront effort.
- `text` (analyzed, full-text searchable) vs. `keyword` (exact-match, used for aggregations/filtering/
  sorting) are different field types for a reason — using `text` where exact matching was needed (or vice
  versa) is a common source of "why doesn't this filter/aggregation work as expected."

## Cluster Health

```bash
GET _cluster/health              # green/yellow/red — yellow means unassigned replica shards, red means
                                  # unassigned primary shards (actual data unavailability)
GET _cat/indices?v&s=store.size:desc
GET _cat/shards?v                 # per-shard allocation, useful for diagnosing hot-spotting
GET _nodes/stats                   # per-node resource usage
```

- **Split-brain protection**: a cluster needs a proper quorum configuration (`discovery.seed_hosts` /
  minimum master-eligible nodes) to avoid split-brain during a network partition — same distributed-
  systems concern as any quorum-based system (Kafka's replication, etcd in `kubeadm`).

## Common Pitfalls

- No ILM/index lifecycle policy, so daily/hourly indices accumulate indefinitely, consuming ever-growing
  disk and eventually degrading cluster performance broadly, not just for the old data.
- Dynamic mapping left on for production data with inconsistent field types across documents, causing
  intermittent indexing failures that are hard to trace back to "which document broke the mapping."
- Cluster `yellow` status ignored as "probably fine" — it means every replica isn't allocated, which is a
  real reduction in fault tolerance even though data is still available; investigate rather than dismiss.
- Using Elasticsearch/OpenSearch purely for log storage when `loki`'s label-indexed, cheaper-at-scale
  model would fit better — full-text indexing of every log line is powerful but expensive; the right
  choice depends on whether queries actually need full-text search across log bodies or just
  label-based filtering (see `loki` skill).
