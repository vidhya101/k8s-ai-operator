---
name: rag-pipeline-design
description: RAG (Retrieval-Augmented Generation) pipeline design — chunking, retrieval quality, and evaluation, as a discipline distinct from the LLM serving infrastructure itself. Use when designing or debugging why a RAG system gives wrong/incomplete answers; pairs with llm-serving and vector-database-operations.
---

# RAG Pipeline Design

The end-to-end design discipline behind a RAG system, complementing `llm-serving`'s inference-infrastructure
focus and `vector-database-operations`'s storage/index focus — this skill is about the pipeline that
connects them and makes retrieval actually good.

## Pipeline Stages

```text
Ingestion   → chunk documents → embed chunks → store in vector DB (+ metadata)
Query time   → embed the user's query → retrieve top-K similar chunks (+ optional metadata filter/
               hybrid search) → assemble prompt with retrieved context → generate with the LLM
```

A wrong answer can originate at any stage — the debugging discipline is inspecting each stage's output
independently (what was actually retrieved? was it relevant? was the prompt assembled correctly?) rather
than treating the whole pipeline as an opaque black box, the same principle `llm-serving` states for RAG
debugging.

## Chunking Strategy

- **Fixed-size chunking** (simple, by token/character count): easy to implement, but can split a
  coherent thought across chunk boundaries, hurting retrieval of exactly the content that matters.
- **Semantic/structure-aware chunking** (by paragraph, section, heading boundaries): better preserves
  meaning per chunk, more implementation effort, generally better retrieval quality for structured
  documents (docs, code, articles with clear sections).
- **Overlap between chunks** (e.g. 10-20% overlap) reduces the boundary-splitting problem at some storage/
  compute cost — a reasonable default unless chunk count/storage is a genuine constraint.
- This is the highest-leverage tuning point in the whole pipeline — before tuning the vector index or
  swapping embedding models, check whether chunking is actually producing coherent, retrievable units.

## Retrieval Quality

- **Re-ranking**: retrieve a larger initial candidate set (e.g. top-50) via fast vector similarity, then
  re-rank with a more expensive, more accurate model (a cross-encoder) down to the final top-K actually
  sent to the LLM — meaningfully improves precision over vector similarity alone, at added latency cost.
- **Hybrid search** (vector + keyword/BM25): catches queries with specific terms/entities/IDs that pure
  embedding similarity handles poorly — see `vector-database-operations`'s note on this.
- **Query transformation**: rewriting or expanding the user's raw query before embedding it (e.g.
  resolving pronouns from conversation history, generating multiple query variants) can substantially
  improve retrieval for conversational/ambiguous queries that don't embed well as-is.

## Evaluation

- RAG systems need their own evaluation, distinct from general LLM eval (`llm-serving`'s guardrails
  section) — retrieval metrics (is the right chunk actually retrieved — precision/recall against a
  labeled test set of query→expected-chunk pairs) separately from generation quality (given the right
  context, did the model answer well) — conflating the two makes it unclear which stage to fix when
  answers are wrong.
- A "golden set" of representative queries with known-correct answers/sources, re-run whenever the
  pipeline changes (new embedding model, new chunking strategy, new prompt template) — the RAG-specific
  form of the `testing` skill's "verify against a reproducing case" discipline.

## Common Pitfalls

- Debugging a bad answer by only looking at the final generated output, never inspecting what was
  actually retrieved — the fastest way to misdiagnose a retrieval failure as a "the model is dumb" issue.
- Chunk size/overlap never tuned against the actual document types in the corpus (code vs. prose vs.
  tables all retrieve differently) — one-size-fits-all chunking across heterogeneous content types.
- No re-ranking stage on a pipeline where the initial vector similarity search returns a noisy candidate
  set — sending the raw top-K straight to the LLM with no quality filter.
- Index/embeddings never refreshed as source documents change, so RAG answers cite stale information —
  same staleness-tolerance question `vector-database-operations` raises, now specifically about answer
  correctness rather than just search relevance.
