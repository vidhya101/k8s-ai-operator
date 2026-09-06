---
name: oracle-database
description: Oracle Database administration and troubleshooting — tablespaces, RMAN backup, Data Guard replication, and AWR performance diagnostics. Use for Oracle-specific schema/query/replication questions; see database-operations for cross-database backup/DR principles.
---

# Oracle Database

See `database-operations` for backup/replication/migration principles that apply across all databases;
this skill covers Oracle-specific mechanics, which differ more from the open-source databases than they
differ from each other.

## Connecting & Inspecting

```bash
sqlplus <user>/<password>@<connect-string>
sqlplus -s <user>/<password>@<connect-string> @script.sql
```

```sql
SELECT * FROM v$session WHERE status = 'ACTIVE';         -- active sessions right now
SELECT * FROM v$sql ORDER BY elapsed_time DESC FETCH FIRST 10 ROWS ONLY;   -- most expensive queries
```

- Prefer a connection method that doesn't put the password on the command line/shell history
  (`sqlplus /@connect-string` with OS authentication, a wallet, or a prompted password) — a password in
  `ps` output or shell history is a real, common leak vector.

## Storage: Tablespaces

- Tables/indexes live in tablespaces (logical storage containers mapped to physical datafiles) —
  running out of space in a tablespace (or its underlying filesystem) halts writes to anything stored
  there; monitoring tablespace free space is a standard, necessary check, not optional housekeeping.

```sql
SELECT tablespace_name, ROUND(used_percent, 1) used_percent
FROM dba_tablespace_usage_metrics ORDER BY used_percent DESC;
```

## High Availability: RAC (Real Application Clusters)

- Multiple instances (on different nodes) share access to one physical database — provides
  compute-level HA (an instance/node failure doesn't take the database down, surviving instances absorb
  the load) and horizontal read/write scaling across nodes, distinct from Data Guard's standby-replica
  model below (RAC is active-active on shared storage; Data Guard is primary/standby with separate
  storage/copies).
- Cache Fusion (the interconnect between instances for sharing buffer cache blocks) is RAC's key
  performance-sensitive component — interconnect latency/bandwidth directly affects multi-instance
  performance; a slow/misconfigured private interconnect network degrades RAC performance in ways that
  look like generic database slowness but are actually cluster-communication-bound.
- RAC and Data Guard are commonly combined (a RAC primary with a Data Guard standby, itself potentially
  RAC) for both node-level HA and site/region-level disaster recovery — know which layer(s) a given
  deployment actually has before assuming a specific failure mode is covered.

```sql
SELECT inst_id, instance_name, status FROM gv$instance;    -- gv$ views span all RAC instances, v$ views
                                                             -- are instance-local — using v$ where gv$
                                                             -- was needed silently misses other instances
```

## Backup: RMAN

- Recovery Manager (RMAN) is Oracle's native backup/recovery tool — handles full/incremental backups,
  archived redo log management, and point-in-time recovery.

```bash
rman target /
RMAN> BACKUP DATABASE PLUS ARCHIVELOG;
RMAN> RESTORE DATABASE; RECOVER DATABASE;    # only ever with explicit confirmation — see safety rule
```

- Archived redo logs must be retained/backed up alongside the database backup itself for point-in-time
  recovery to work — a database backup with no corresponding archive log retention can only restore to
  the exact backup time, not to an arbitrary point after it.

## Replication/HA: Data Guard

- Oracle's native primary/standby replication — physical standby (block-for-block copy via redo apply) or
  logical standby (SQL-level apply, allows the standby to be used for other purposes concurrently).
- Protection modes (`Maximum Availability`, `Maximum Performance`, `Maximum Protection`) trade durability
  guarantees against primary-database performance impact — same synchronous-vs-asynchronous tradeoff as
  any other database's replication, know which mode is configured before assuming an RPO.

## Performance Diagnostics: AWR

- Automatic Workload Repository (AWR) reports summarize database performance over a time window (wait
  events, top SQL by resource consumption, I/O) — the standard first artifact to pull when investigating
  an Oracle performance issue, analogous to `EXPLAIN ANALYZE` but at the whole-database/workload level
  rather than a single query.

## Common Pitfalls

- A tablespace approaching 100% used with no alerting configured, silently halting writes when it fills —
  same class of issue as `linux` skill's disk-full pitfall, but at the tablespace layer instead of the
  filesystem layer (both need monitoring; filesystem free space doesn't guarantee tablespace free space).
- RMAN backups running successfully but archived redo logs not retained long enough for the actual
  recovery point objective — a "successful backup" that can't actually meet the required RPO.
- Password embedded directly in a connect string on the command line, landing in shell history/process
  list.
- A Data Guard standby that's been silently lagging (apply lag) for an extended period, discovered only
  when a failover is actually needed and the standby turns out to be far behind.
