---
name: database-schema-migrations
description: Schema migration tooling — Liquibase and Flyway — versioned, repeatable, rollback-aware database changes. Use when setting up or reviewing a migration tool/changelog, complementing database-operations' migration-safety principles with the actual tooling mechanics.
---

# Schema Migration Tooling (Liquibase, Flyway)

The concrete tooling behind `database-operations`' migration-safety principles (forward-only where
practical, matching locking behavior, rollback path). Both tools solve the same core problem — versioned,
repeatable, team-shareable schema changes — with different authoring styles.

## Core Model (shared by both)

- Migrations are ordered, versioned files applied sequentially, tracked in a metadata table in the target
  database itself (`DATABASECHANGELOG` for Liquibase, `flyway_schema_history` for Flyway) — this tracking
  table is what makes "which migrations have already run against this specific database" a reliable,
  queryable fact instead of tribal knowledge.
- **Never edit an already-applied migration file** — once a migration has run anywhere (including a
  teammate's local database), it's immutable; a needed correction is a *new* migration, not an edit to an
  old one. Editing an applied migration desyncs the checksum tracking and can silently corrupt what the
  tool believes has been applied where.

## Flyway (SQL- or Java-based, simpler model)

```text
V1__create_users_table.sql
V2__add_email_index.sql
V3__add_status_column.sql
```

```bash
flyway migrate           # apply all pending migrations, in version order
flyway info                # what's applied, what's pending
flyway validate             # checksum-verify applied migrations against the files, catches tampering
```

- Versioned (`V*`) migrations are forward-only by design; `U*` (undo) migrations exist but require the
  paid edition — the free/community pattern is typically "roll forward with a corrective migration"
  rather than relying on built-in rollback.

## Liquibase (XML/YAML/SQL changelogs, richer rollback model)

```yaml
databaseChangeLog:
  - changeSet:
      id: 1
      author: team
      changes:
        - createTable: { tableName: users, columns: [...] }
      rollback:
        - dropTable: { tableName: users }    # explicit rollback defined alongside the forward change
```

- Built-in rollback support is a first-class, free-edition feature (unlike Flyway's community edition) —
  worth the choice when rollback tooling genuinely matters for a project's risk tolerance, at the cost of
  a more verbose authoring format than plain SQL files.
- Supports database-agnostic changelog syntax (`createTable`, `addColumn`) that generates the right SQL
  dialect per target database — useful for a codebase that must support multiple database engines; adds
  an abstraction layer to reason about versus writing raw SQL directly.

## Common Pitfalls

- A migration that locks a large table for its duration run against production without checking that
  specific operation's locking behavior on the specific engine/version first — identical warning
  `database-operations` gives, just now with the concrete tool that will actually execute it.
- Migration files renamed/edited after being applied somewhere, breaking checksum validation or version
  ordering for anyone who already ran the original.
- Migrations not run in CI against a fresh database as part of the test suite — schema drift between
  what's documented in migrations and what's actually deployed goes undetected until it causes a real
  failure.
- Relying on manual, undocumented database changes "just this once" instead of a migration file — the
  exact problem versioned migrations exist to prevent; every schema change should go through the tool.
