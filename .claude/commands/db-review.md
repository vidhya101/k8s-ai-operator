---
description: Review database schema, indexing, backup/restore posture, and replication/failover configuration.
argument-hint: "[optional: specific migration, schema file, or 'backup strategy']"
---

Review the database setup at: $ARGUMENTS (default: infer the engine(s) in use from the repo and review
what's present — schema files, migrations, backup/replication config).

Delegate to the `database-reliability-engineer` agent, using the engine-specific skill (`mysql`/
`postgresql`/`mongodb`/`oracle-database`) that matches what's actually in use, plus `database-operations`
for the cross-engine backup/replication/migration principles.

1. Identify the engine(s) and version(s) in use before reviewing anything engine-specific — locking
   behavior, replication model, and available tooling differ meaningfully by engine/version.
2. If a migration is in scope: check its locking behavior on this engine/version, whether it has a
   rollback path, and whether it stays compatible with a rolling deploy (old and new app code running
   simultaneously against the same schema).
3. If backup/DR is in scope: confirm what's actually backed up, the retention policy, and — critically —
   whether a restore has ever actually been tested, not just assumed to work because the backup job
   reports success.
4. Check credentials aren't embedded in application config/code (see `.claude/rules/secrets.md`) and that
   a connection pooler is in place at any real scale.

Never run a mutating database command (`DROP`, `DELETE`, `ALTER`, `TRUNCATE`, an actual restore) as part
of this review — read-only inspection only, per `.claude/rules/safety.md`.
