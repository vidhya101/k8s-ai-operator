---
name: postgresql
description: PostgreSQL administration and troubleshooting — indexing, EXPLAIN ANALYZE, vacuuming, and replication. Use for PostgreSQL-specific schema/query/replication questions; see database-operations for cross-database backup/DR principles.
---

# PostgreSQL

See `database-operations` for backup/replication/migration principles that apply across all databases;
this skill covers PostgreSQL-specific mechanics.

## Connecting & Inspecting

```bash
psql -U <user> -h <host> -d <database>
psql -c "SELECT * FROM pg_stat_activity WHERE state != 'idle';"    # active queries right now
pg_dump --format=custom <db> > backup.dump                          # logical backup
```

## Query Performance

```sql
EXPLAIN ANALYZE SELECT ...;    -- actual execution plan with real timing, not just the estimate
```

- Look for a sequential scan (`Seq Scan`) on a large table where an index scan was expected — usually a
  missing index, a query that can't use an existing index (e.g. a function applied to the indexed column
  without a matching expression index), or the planner's cost estimates being off due to stale statistics.
- `ANALYZE <table>` refreshes the planner's statistics — if the plan looks wrong for a table with recently
  changed data volume/distribution, stale statistics are a common, easy-to-check cause.

## Vacuuming (PostgreSQL-specific, not optional)

- PostgreSQL's MVCC model means updated/deleted rows aren't immediately reclaimed — `VACUUM` reclaims
  space and updates visibility metadata; `autovacuum` does this automatically but can fall behind on
  high-write tables.
- **Transaction ID wraparound** is a real failure mode if autovacuum is disabled or misconfigured on a
  high-write table for long enough — check `age(datfrozenxid)` if a database has had autovacuum tuning
  issues; this is a "database stops accepting writes" class of incident, not a performance nit.

```sql
SELECT relname, n_dead_tup, last_autovacuum FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;
```

## Replication

- Streaming replication (physical, WAL-based) for read replicas/HA — `pg_stat_replication` on the primary
  shows replica lag; a replica behind on WAL application serves stale reads.
- Logical replication (row-level, selective table/publication-based) for more targeted sync (e.g.
  replicating a subset of tables to a different schema/version) — different use case than physical
  streaming replication, don't conflate the two.
- Managed offerings (RDS PostgreSQL, Azure Database for PostgreSQL, Cloud SQL) automate failover — same
  caution as MySQL: confirm the actual failover model and RPO/RTO rather than assuming.

## Common Pitfalls

- Autovacuum tuned too conservatively (or disabled) on a high-churn table, leading to table/index bloat
  and eventually transaction ID wraparound risk on a long enough horizon.
- Connection count exhaustion — PostgreSQL's per-connection process model means many idle connections
  consume real memory; a connection pooler (PgBouncer, or the cloud provider's managed pooling) is often
  needed at any real application scale, not optional.
- An index created but never used (`pg_stat_user_indexes.idx_scan = 0` over a meaningful time window) —
  costs write overhead with no read benefit; worth periodically auditing.
- `EXPLAIN` (without `ANALYZE`) reviewed alone — shows the planner's *estimate*, not what actually
  happened; `EXPLAIN ANALYZE` (which actually executes the query) is needed to see real timing/row counts.
