---
name: vector-database-operations
description: Vector databases (Pinecone, Weaviate, Milvus, pgvector) — index types, embedding pipeline design, and operational concerns for similarity search at scale. Use when standing up or troubleshooting a vector store, typically backing a RAG pipeline (see rag-pipeline-design) or a recommendation/search system.
---

# Vector Database Operations

Stores embeddings (dense numeric vectors representing meaning) and serves approximate-nearest-neighbor
similarity search over them — the retrieval backbone behind RAG (`rag-pipeline-design`) and semantic
search/recommendation systems. Distinct operational profile from the relational/document databases
elsewhere in this stack: the core operation is "find the K most similar vectors," not exact lookups or
transactions.

## Index Types (the main tuning lever)

- **HNSW** (Hierarchical Navigable Small World): the most common choice — very fast approximate search,
  higher memory usage, index build time grows with data size. Good default for most workloads under
  tens of millions of vectors.
- **IVF** (Inverted File Index): partitions vectors into clusters, searches only relevant clusters —
  lower memory than HNSW, faster to build, somewhat lower recall for the same speed unless tuned
  carefully (`nprobe` parameter controls the recall/speed tradeoff).
- **Exact (flat) search**: no approximation, always correct, but scales linearly with dataset size — fine
  for a small enough collection, becomes impractical past roughly hundreds of thousands of vectors
  depending on latency requirements.
- The index type is an accuracy/speed/memory tradeoff, not a free choice — pick based on actual scale and
  latency requirements, not by default; re-evaluate if the collection grows an order of magnitude.

## Managed vs. Self-Hosted vs. Extension

- **Managed** (Pinecone): no infrastructure to operate, scales automatically, but a recurring cost and
  another vendor dependency.
- **Self-hosted** (Weaviate, Milvus, Qdrant): full control, runs on your own infrastructure (often
  Kubernetes — apply the same `kubernetes` resource/HA discipline as any other stateful workload), more
  operational burden.
- **Extension of an existing database** (pgvector for PostgreSQL): avoids introducing a whole new
  datastore when vector search is a secondary need alongside an already-relational workload — simpler
  operationally, but doesn't match a dedicated vector database's performance at very large scale/high
  query volume.
- Don't default to a dedicated vector database for a small-scale, secondary similarity-search need when
  `pgvector` on an already-existing Postgres instance would do — same anti-over-engineering principle as
  everywhere else in this stack (Section 1.2).

## Embedding Pipeline Considerations

- **Embedding model consistency**: vectors from different embedding models (or even different versions of
  the same model) aren't comparable — re-embedding the entire collection is required after a model
  change, not just new documents; a mixed collection from different model versions silently returns
  nonsensical similarity results with no error.
- **Chunking strategy** (for text) directly affects retrieval quality — too large a chunk dilutes
  relevance (the whole chunk is returned even if only one sentence matters); too small loses context —
  this is the single highest-leverage tuning point for retrieval quality, more than index type choice.
- **Metadata filtering**: combining vector similarity with structured filters (e.g. "similar documents,
  but only from this tenant/date range") — verify the store supports efficient filtered search rather
  than a slow post-filter over an unfiltered top-K result, which silently returns fewer relevant results
  than expected when the filter is selective.

## Common Pitfalls

- Re-embedding forgotten after switching embedding models, leaving stale vectors from the old model mixed
  into the collection with new ones — searches silently degrade with no error.
- Index parameters (HNSW's `ef_construction`/`M`, IVF's `nprobe`) left at defaults never tuned against
  actual recall/latency requirements, measured with a real evaluation set rather than assumed.
- No tenant/access-control isolation on a multi-tenant vector store, risking cross-tenant data exposure
  through similarity search results — apply the same least-privilege/isolation discipline as any other
  multi-tenant datastore.
- Treating vector search as a complete solution rather than one component — hybrid search (combining
  vector similarity with traditional keyword/BM25 search) often outperforms pure vector search for
  queries with specific terms/entities that embedding similarity alone handles poorly.
