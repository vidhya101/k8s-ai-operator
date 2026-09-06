---
name: mysql
description: MySQL/MariaDB administration and troubleshooting — indexing, replication, and common performance issues. Use for MySQL-specific schema/query/replication questions; see database-operations for cross-database backup/DR principles.
---

# MySQL / MariaDB

See `database-operations` for backup/replication/migration principles that apply across all databases;
this skill covers MySQL-specific mechanics.

## Connecting & Inspecting

```bash
mysql -u <user> -p -h <host> <database>
mysql -e "SHOW PROCESSLIST;"                      # active connections/queries right now
mysql -e "SHOW ENGINE INNODB STATUS\G"              # InnoDB internals — locks, deadlocks
mysqldump --single-transaction <db> > backup.sql    # logical backup, consistent snapshot without locking
                                                     # (InnoDB only; --single-transaction needs InnoDB)
```

## Indexing & Query Performance

```sql
EXPLAIN SELECT ...;                    -- query plan: check for `type: ALL` (full table scan) on large
                                        -- tables, which usually means a missing/unused index
SHOW INDEX FROM my_table;
SELECT * FROM information_schema.processlist WHERE time > 5;   -- long-running queries right now
```

- A missing index on a frequently-filtered/joined column is the single most common cause of slow MySQL
  queries at scale — `EXPLAIN` before assuming the database itself is the bottleneck.
- Composite index column order matters: an index on `(a, b)` serves queries filtering on `a` or `(a, b)`
  efficiently, but not queries filtering on `b` alone.

## Replication

- Traditional binlog replication (statement-based, row-based, or mixed) — row-based is generally safer
  (deterministic) for anything with non-deterministic statements (e.g. `NOW()`, `UUID()`).
- Replication lag is the key thing to monitor (`SHOW REPLICA STATUS` /`Seconds_Behind_Source`) — an
  application reading from a lagging replica can see stale data; know whether a given read path is
  replica-tolerant before routing reads there.
- Managed offerings (RDS MySQL, Azure Database for MySQL, Cloud SQL) handle failover automation — confirm
  which failover model (synchronous Multi-AZ vs. async read replica promotion) a given deployment uses
  before assuming an RPO of zero.

## Common Pitfalls

- `mysqldump` run without `--single-transaction` against an InnoDB table under active writes, producing
  either a locking backup (blocks writes) or an inconsistent snapshot.
- Character set/collation mismatches between application, connection, and table definitions causing
  subtle string comparison or storage issues (especially with emoji/multi-byte UTF-8 needing `utf8mb4`,
  not the legacy `utf8` alias which is actually a 3-byte-max subset).
- `SELECT *` in application code masking exactly which columns/indexes a query actually depends on,
  making it harder to reason about index coverage.
- Long-running transactions left open (e.g. a debug session with an uncommitted transaction) holding
  locks that block other queries in ways that look like unrelated slowness.
