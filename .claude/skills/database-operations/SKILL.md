---
name: database-operations
description: Cross-database operational principles — backup/restore verification, replication/failover, connection pooling, and schema migrations. Use alongside a specific database skill (mysql/postgresql/mongodb/oracle-database) for the engine-agnostic parts of database reliability work.
---

# Database Operations (Cross-Engine)

Operational principles that apply regardless of which database engine is in use — pair with `mysql`,
`postgresql`, `mongodb`, or `oracle-database` for engine-specific syntax/mechanics, and the
`database-reliability-engineer` agent for a structured review.

## Backup & Restore

- A backup that has never been restored and verified is not a backup, it's an unverified assumption —
  schedule periodic restore tests (to a scratch environment), not just backup jobs.
- Know the backup type in use and what it actually protects against: full logical dump (portable, slow
  for large DBs), physical/snapshot backup (fast, often storage-layer/cloud-native, less portable across
  engine versions), and whether point-in-time recovery (via transaction/WAL/redo log retention) is
  available or only fixed backup-time restore points.
- Backup retention should be driven by a stated RPO/compliance requirement, not an arbitrary default —
  see `.claude/skills/architecture-review` for how to surface this as a decision rather than assume it.

## Replication & Failover

- Synchronous replication (write isn't acknowledged until the replica confirms) gives near-zero RPO at
  the cost of write latency and potential availability impact if the replica is unreachable; asynchronous
  replication is faster but can lose the most recent writes on an unplanned failover — this tradeoff
  exists in every engine's replication model under different names (see the engine-specific skills).
- Test failover, not just replication lag monitoring — a replica that's been silently unable to actually
  be promoted (permissions, network, configuration drift) isn't providing the HA it appears to.
- Read replicas serve stale data by the amount of current replication lag — know which read paths in the
  application can tolerate that staleness and which need the primary.

## Connection Management

- Connection pooling (application-side, or a dedicated pooler like PgBouncer/ProxySQL) matters at any
  real scale — most databases have a real per-connection resource cost (memory, and for some engines a
  full OS process), and "just open more connections" doesn't scale indefinitely.
- Connection limits hit under load look like a database performance problem but are a connection
  management/pooling gap — check active connection count against the configured max before assuming the
  database itself is the bottleneck.

## Schema Migrations

- Migrations should be forward-only and reversible where practical (a paired down-migration, or a
  documented manual rollback procedure) — treat a migration with no rollback path as higher-risk and flag
  it explicitly.
- A migration that locks a large table for its duration (adding a column with a default value on some
  engines/versions, rebuilding an index) can cause a production outage disguised as "just a schema
  change" — check whether the specific engine/version does this operation online or with a blocking lock
  before running it against a live table.
- Backward compatibility during a rolling deploy: if old and new application code run simultaneously
  during a rollout, the schema must support both versions' expectations for the duration — a migration
  that drops a column the old code still reads breaks the deploy mid-rollout.

## Common Pitfalls (cross-engine)

- Backups verified only by "the job reported success," never by an actual restore.
- No monitoring on replication lag, connection count, or storage/tablespace free space — these are the
  three most common "silent until it's an incident" database failure precursors across every engine.
- A destructive migration (dropping a column/table) run in the same deploy that stops using it, instead
  of a separate later migration after confirming nothing still depends on it — see
  `.claude/rules/safety.md`'s blast-radius confirmation principle, which applies directly to schema changes.
- Credentials for database access embedded in application config/code instead of a secret manager
  (see `vault`/`.claude/rules/secrets.md`) — the same secret-handling discipline applies to DB credentials
  as to any other credential.
