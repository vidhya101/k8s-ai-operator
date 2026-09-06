---
name: redis
description: Redis — in-memory data store for caching, session storage, and pub/sub, including eviction policy, persistence tradeoffs, and cluster/replication modes. Use for caching-layer design/troubleshooting or when Redis is used as a primary data store.
---

# Redis

In-memory key-value store — primarily used as a cache, but also as a session store, rate-limiter backend,
pub/sub bus, or (with persistence configured) a lightweight primary datastore. See `database-operations`
for backup/replication principles that still apply when Redis holds data that matters.

## Caching Patterns

- **Cache-aside** (most common): application checks Redis first, falls back to the source of truth
  (database) on a miss, then populates the cache — application code owns cache population; Redis stays a
  pure cache.
- **Write-through**: writes go to Redis and the database together — keeps the cache always warm, at the
  cost of write latency including the cache write.
- **Invalidation** is the hard part of any cache: TTL-based expiry (simple, but serves stale data for up
  to the TTL window) vs. explicit invalidation on write (fresher, but requires reliably catching every
  write path that should invalidate a given key — a missed invalidation path is a silent staleness bug).

## Eviction Policy (when memory fills up)

```text
noeviction        — reject new writes once memory limit is hit (correct for Redis-as-primary-store,
                     where losing data unexpectedly is unacceptable)
allkeys-lru        — evict least-recently-used keys across the whole keyspace (typical cache default)
volatile-lru        — evict LRU only among keys with a TTL set (keeps non-expiring keys safe from eviction)
allkeys-lfu/volatile-lfu — evict by least-frequently-used instead of least-recently-used
```

Picking the wrong policy for the use case is a common source of confusing behavior: `noeviction` on a
cache-only deployment causes writes to start failing under memory pressure instead of just evicting old
entries; `allkeys-lru` on a deployment using Redis as a primary store can silently evict data that was
never meant to expire.

## Persistence (if Redis holds data you can't afford to lose)

- **RDB** (point-in-time snapshots): compact, fast restarts, but can lose writes since the last snapshot.
- **AOF** (append-only log of writes): more durable (configurable fsync frequency), larger files, slower
  restart (replays the log) — same durability-vs-performance tradeoff as any WAL-based system.
- Pure-cache deployments often run with persistence disabled entirely (a cold cache after restart is
  cheap to refill) — deliberately decide this per deployment rather than leaving it at a default that
  doesn't match the actual use case.

## Replication & Clustering

- **Replica sets** (primary + read replicas) for read scaling and failover, with Redis Sentinel managing
  automatic failover — replication is asynchronous by default, so a failover can lose the most recent
  writes, same tradeoff class as any async replication (`database-operations`).
- **Redis Cluster** for horizontal scaling beyond one node's memory — data is sharded across nodes by hash
  slot; multi-key operations spanning different hash slots aren't atomic the way they are on a
  single-node Redis, which affects application logic that assumes single-node transactional semantics.

## Common Pitfalls

- Eviction policy mismatched to use case (`noeviction` silently rejecting writes on a cache; `allkeys-lru`
  silently losing data meant to be permanent).
- No monitoring on memory usage/eviction rate — a cache approaching its memory limit degrades
  (increasing eviction, lower hit rate) well before it becomes an outright failure, and that degradation
  is invisible without metrics.
- Large keys or unbounded data structures (an ever-growing list/set/hash with no expiry or size cap)
  causing memory pressure and, on Cluster, hot-shard imbalance.
- Redis used as a primary store with persistence disabled "because it's just Redis" — a decision that
  should be explicit and reviewed, not a default nobody actually chose on purpose.
