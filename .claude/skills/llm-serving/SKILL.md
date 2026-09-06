---
name: llm-serving
description: Serving and operating LLM/GenAI inference endpoints — vLLM for high-throughput serving, RAG architecture, and prompt/token-level monitoring and guardrails. Use when deploying, scaling, or monitoring an LLM-backed service, distinct from classical ML model serving (see kserve).
---

# LLM / GenAI Serving

Serving large language models has different operational characteristics than classical ML model serving
(`kserve` skill) — token-by-token generation, much larger memory footprints, and a different failure/abuse
surface (prompt injection, cost-per-request variability). Treat this as its own discipline, not just
"KServe but bigger."

## Serving: vLLM (and similar high-throughput engines)

- **Continuous batching**: dynamically batches incoming requests at the token level rather than waiting
  to fill a fixed batch — dramatically improves throughput over naive request-level batching for
  variable-length generation workloads, which is most of what makes vLLM (and similar engines like TGI)
  worth using over a naive `transformers`-based serving loop.
- **KV cache management** (PagedAttention in vLLM specifically): the attention key-value cache is the
  dominant GPU memory consumer during generation — efficient cache management is what allows serving many
  concurrent requests without either wasting memory (over-allocating per-request) or OOMing.
- Autoscaling an LLM-serving deployment on CPU/memory utilization (the default Kubernetes HPA metric,
  see `kubernetes-autoscaling`) is usually the wrong signal — GPU utilization or, better, a queue-depth/
  request-latency-based custom metric reflects actual serving capacity far more accurately.

```bash
python -m vllm.entrypoints.openai.api_server --model <model> --tensor-parallel-size <N>
curl http://localhost:8000/v1/chat/completions -d '{"model": "...", "messages": [...]}'
```

## RAG (Retrieval-Augmented Generation) Architecture

- Retrieval (a vector DB query against embedded documents) + generation (the LLM call with retrieved
  context injected into the prompt) — the retrieval step's quality bounds the generation's quality; a
  RAG system producing wrong answers is very often a retrieval problem (bad embeddings, wrong chunk size,
  stale index), not a model problem.
- Frameworks like LangChain/LlamaIndex provide the orchestration glue (chunking, retrieval, prompt
  assembly) — useful for prototyping; for a production system, understand what the framework is actually
  doing at each step rather than treating it as an opaque black box, since debugging a bad RAG response
  requires inspecting the retrieved context, not just the final output.
- Index freshness: a vector index built once and never updated silently drifts from the source-of-truth
  documents — needs the same "is this actually kept in sync" scrutiny as any cache/materialized view.

## Monitoring & Guardrails

- Token-level metrics (input/output token counts, time-to-first-token, tokens/sec) matter alongside
  request-level RED metrics (see `prometheus` skill) — token count directly drives cost, and
  time-to-first-token is often the user-perceived latency metric that matters most for a streaming response.
- **Guardrails**: input validation (prompt injection detection, PII scrubbing before the prompt reaches
  the model) and output validation (content filtering, schema validation for structured outputs) — treat
  as a security boundary, not an optional nicety, especially for any endpoint accepting user-supplied text
  that gets included in a prompt.
- Cost is usage-variable in a way traditional serving isn't (cost scales with token count, not just
  request count) — the `principal-finops-engineer` agent's rightsizing lens applies, but the actual lever
  is often prompt/context length and max-token limits, not just replica count.

## Common Pitfalls

- Autoscaling on CPU/memory for a GPU-bound serving workload — the autoscaler reacts to the wrong signal
  and either under- or over-scales relative to actual serving capacity.
- No guardrail on max output tokens/context length, letting a single request consume disproportionate
  cost/latency with no ceiling.
- A RAG system's retrieved context never inspected during debugging — treating the whole pipeline as one
  black box makes it impossible to tell whether a bad answer is a retrieval failure or a generation failure.
- User-supplied text concatenated directly into a system prompt with no separation/sanitization, opening a
  prompt-injection path into the system's own instructions.
