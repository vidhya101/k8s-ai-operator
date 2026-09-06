---
name: mimir
description: Grafana Mimir — horizontally-scalable, multi-tenant, long-term-retention Prometheus-compatible metrics storage. Use when Prometheus's single-node retention/scale limits are the actual problem, not for general PromQL questions (see the prometheus skill for that).
---

# Mimir

A drop-in remote-write target and query backend for Prometheus that adds horizontal scalability,
long-term retention, and multi-tenancy. PromQL itself is unchanged — see the `prometheus` skill for query
and instrumentation guidance; this skill covers what's specific to running Mimir as the storage layer.

## When Mimir Is the Right Answer

- Single-node Prometheus is hitting retention limits (need months/years of history, not the local disk's
  practical ~weeks) or memory/cardinality limits from scale.
- Multiple teams/clusters need centralized, long-term metrics storage with tenant isolation (Mimir's
  multi-tenancy via `X-Scope-OrgID`).
- Global querying across multiple Prometheus instances/clusters is needed without manually federating.

Don't introduce Mimir just because it's the "more scalable" option if a single Prometheus instance with
appropriate retention already meets the actual requirement — that's speculative complexity (Section 1.2).

## Architecture Essentials

- Prometheus instances remote-write to Mimir instead of (or in addition to) local storage.
- Mimir separates ingestion, storage (object storage — S3/GCS/Azure Blob backed), and querying into
  independently scalable components — relevant when troubleshooting where a bottleneck actually is
  (ingester vs. querier vs. store-gateway).
- Multi-tenancy isolates metrics per `X-Scope-OrgID` header — queries and writes must include the correct
  tenant ID or they'll silently go to/come from the wrong (or default) tenant.

## Key Commands / Checks

```bash
curl -H "X-Scope-OrgID: <tenant>" <mimir>/prometheus/api/v1/query?query=up
mimirtool config convert --config-file=prometheus.yml    # migrate a Prometheus config
mimirtool rules load <rules-file>                         # manage alerting/recording rules in Mimir
mimirtool analyze prometheus --address=<prom> ...          # cardinality analysis before migrating
```

## Common Pitfalls

- Missing or wrong `X-Scope-OrgID` on a query, silently hitting the wrong tenant's data (or the
  `anonymous`/default tenant if multi-tenancy isn't strictly enforced).
- Remote-write without a local buffer/queue configured, losing metrics during a network blip to Mimir.
- High-cardinality metrics that were already a problem in Prometheus carried over unchanged into Mimir —
  Mimir scales further, but cardinality discipline (see `prometheus` skill) still matters directly for cost.
- Retention/compaction settings not matched to actual query patterns, causing slow long-range queries
  against un-downsampled raw data.
