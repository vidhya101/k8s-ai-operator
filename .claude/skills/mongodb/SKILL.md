---
name: mongodb
description: MongoDB administration and troubleshooting — schema/index design, replica sets, and sharding. Use for MongoDB-specific document-model/query/cluster questions; see database-operations for cross-database backup/DR principles.
---

# MongoDB

See `database-operations` for backup/replication/migration principles that apply across all databases;
this skill covers MongoDB-specific mechanics.

## Connecting & Inspecting

```bash
mongosh "mongodb://<host>/<database>"
mongosh --eval "db.currentOp({'active': true})"       # active operations right now
mongodump --uri="<connection-string>" --out=backup/    # logical backup
```

## Schema & Index Design

- MongoDB's flexible schema doesn't mean "no schema" — an application still has an implicit schema; a
  document model that varies wildly per document makes queries and indexing much harder to reason about.
  Schema validation (`$jsonSchema` in a collection's validator) can enforce structure without giving up
  flexibility entirely.
- Index every field used in a query's filter/sort — same principle as relational databases, but easier to
  miss since MongoDB won't error on an unindexed query, it'll just do a full collection scan silently.

```javascript
db.collection.find({ status: "active" }).explain("executionStats")   // check `stage: "COLLSCAN"`
                                                                      // (full scan) vs `IXSCAN` (indexed)
db.collection.getIndexes()
db.collection.createIndex({ status: 1, createdAt: -1 })              // compound index
```

- Compound index field order matters, same as SQL databases: index on `(a, b)` serves filters on `a` or
  `(a, b)`, not `b` alone (with the exception of the specific ESR — Equality, Sort, Range — ordering rule
  for compound indexes with sort/range components).

## Replica Sets

- MongoDB's HA/replication unit — a primary handles writes, secondaries replicate the oplog; automatic
  failover elects a new primary if the current one becomes unavailable.
- Write concern (`w: "majority"` vs. `w: 1`) trades durability for latency — `w: "majority"` waits for
  acknowledgment from a majority of replica set members before confirming a write, protecting against
  data loss on a primary failover; `w: 1` is faster but can lose an unacknowledged write on failover.
- Read preference (`primary`, `secondaryPreferred`, etc.) determines whether reads can go to a
  (potentially lagging) secondary — same staleness tradeoff as any read-replica setup.

## Sharding (horizontal scale beyond a single replica set)

- Shard key choice is close to irreversible in practice (resharding is possible in modern MongoDB but
  costly) — a poorly chosen shard key (low cardinality, monotonically increasing, or mismatched to actual
  query patterns) causes uneven data/load distribution ("jumbo chunks," hot shards) that's painful to fix
  after the fact. Get this reviewed before committing to it, not after.

## Common Pitfalls

- A query with no supporting index running a full `COLLSCAN` on a large collection with no error, just
  silent slowness — always check `.explain()` on a slow query rather than assuming an index exists.
- Unbounded array growth inside a single document (e.g. appending events to an array indefinitely) —
  MongoDB documents have a 16MB size limit, and large documents also hurt read/write performance well
  before hitting it.
- `w: 1` write concern used for data where losing an unacknowledged write on failover is actually
  unacceptable — a durability decision made implicitly by leaving the default rather than deliberately.
- A shard key chosen for convenience (e.g. `_id` or a timestamp) without checking it against actual query
  and write distribution patterns first.
