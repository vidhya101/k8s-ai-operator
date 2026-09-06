---
name: prompt-and-context-engineering
description: Prompt and context engineering — structuring instructions, examples, and retrieved context for reliable LLM output, and managing context window budget. Use when writing/debugging a system prompt or agent instructions, or when an LLM's output quality seems tied to how a request was framed rather than a model/infra limitation.
---

# Prompt & Context Engineering

The discipline behind getting reliable output from an LLM — distinct from `llm-serving` (the inference
infrastructure) and `rag-pipeline-design` (the retrieval pipeline feeding context in); this is about how
the instructions and context themselves are structured once you have them.

## Structuring Instructions

- **Specificity beats brevity**: "summarize this" underspecifies length, tone, audience, and what to
  prioritize; "summarize this in 3 bullet points for a non-technical exec, focused on business impact"
  removes the ambiguity that causes inconsistent output across runs.
- **Examples (few-shot) anchor format better than description alone** — showing 1-2 examples of the
  desired input→output shape is often more reliable than describing the desired format in prose,
  especially for structured output (a specific JSON shape, a specific report format).
- **Explicit failure/edge-case handling**: telling the model what to do when information is missing or
  ambiguous ("if you don't have enough information, ask rather than guess") prevents confident-sounding
  fabrication in the gap — the same principle this very repository's `CLAUDE.md` Section 1.1 encodes for
  Claude Code itself ("ask before proceeding when requirements are materially unclear").

## Context Window Budget

- Context is a finite, shared resource — everything included (system prompt, tool definitions,
  conversation history, retrieved documents) competes for the same budget, and irrelevant content doesn't
  just waste space, it can dilute the signal the model needs to attend to for the actual task.
- **Order matters less than relevance** for most modern long-context models, but recency still has some
  effect — don't rely on burying an important instruction in the middle of a huge context block and
  expect it to be weighted equally with something near the start or end.
- This repository's own skill-loading design (`.claude/README.md`'s "why skills instead of one giant
  CLAUDE.md" section) is a direct, concrete application of this principle: load only what's relevant to
  the current task, not everything that might conceivably be useful.

## Common Techniques

- **Chain-of-thought / explicit reasoning steps**: asking a model to reason step-by-step before
  concluding improves accuracy on multi-step problems — the cost is more output tokens/latency, so apply
  it to genuinely non-trivial tasks, not every request.
- **Role/persona framing**: "you are a senior security engineer reviewing this for vulnerabilities" can
  usefully narrow the model's focus and output style — this repository's own `.claude/agents/*.md` personas
  are a structured, reusable form of exactly this technique.
- **Structured output constraints** (a JSON schema, a specific template) reduce format-parsing failures
  downstream — worth the extra specification effort whenever the output feeds into another system rather
  than being read directly by a human.

## Common Pitfalls

- Vague instructions blamed on "the model isn't good enough" when the actual issue is underspecified
  intent — the same ambiguity that would confuse a human collaborator confuses the model, often in a more
  costly way since there's no follow-up clarifying question by default.
- Context stuffed with everything potentially relevant "just in case," diluting the signal and wasting
  budget that could hold more directly useful content (see `mcp-memory`'s `read_graph()` vs. targeted
  `search_nodes()` warning — the same principle, different mechanism).
- No explicit guidance for the ambiguous/missing-information case, leading to confident fabrication
  instead of the model flagging the gap.
- Prompt iterated on by trial and error with no systematic evaluation (see `llm-serving`'s guardrails/
  evaluation discussion) — changes that "feel like" they helped without a real before/after comparison
  against representative cases.
