---
name: provider-routing
description: Claude → Codex → Ollama fallback chain — when to swap tiers (throttled / breaker / task-fit), what MUST stay on primary tier (design, security, incident), Michael's routing discipline. Load when an agent is deciding whether to hand off to a fallback peer, or when Michael is planning a multi-manager delegation.
---

The team runs on a **priority chain of LLM providers**, not on any single one.
Every manager knows this policy so work keeps flowing when the primary tier hits
its ceiling.

## The priority chain

```
1. Claude   (primary — the roster's 12 claude-primary managers)
     ↓  Claude subscription rate-limited, or agent's tokenCap exhausted
2. Codex    (mid-tier — 12 codex-fallback managers, one per domain)
     ↓  OpenAI API limit hit or unavailable
3. Ollama   (local — ambient worker(s), free but slower and less capable)
```

Michael (orchestrator / god) applies the chain when he routes work.

## Which tier for which work

- **Claude (primary)** — architecture, design reviews, security audits, cross-manager
  synthesis, any work where the wrong answer costs real money or a real outage.
- **Codex (fallback)** — code writing, mechanical refactors, YAML/manifest generation,
  routine terraform module wiring. Anything where the correctness bar is "compiles +
  tests pass" rather than "veteran-level judgment call".
- **Ollama (local)** — log summarization, doc drafting, obvious-answer questions,
  ambient always-on background chores. Anything that would burn tokens on a cloud
  provider for a task a 7B model can handle.

## When to swap tiers

- **User asked for it** — "use ollama for this", "route through codex" — obey.
- **The active tier's circuit breaker fires** — Munder's `breaker.ts` message
  "Circuit breaker: constrain" means STOP the current tier's spending. Route
  next similar task to the tier below.
- **Anthropic hourly limit hit** (`ctx exhausted`, `rate_limited`) — Michael
  swaps to codex-fallback peer for that domain and notes it in `who-did-what.md`.
- **Task class matches a lower tier by nature** — a log-summarization task
  never needed Claude; Michael sends it straight to an Ollama worker.

## What agents MUST do

- Before assuming Claude is available, don't. If a task times out or errors with
  rate/limit language, mark the finding in the current task's `tokens.md` and
  delegate to the `<same-name>-codex` peer (see roster).
- Never silently downgrade a task that materially needs the primary tier (design,
  security, incident response) — escalate to the user instead.
- Attribute the tier used for load-bearing conclusions in the final synthesis so
  the user can weigh confidence.

## What Michael MUST do

- Keep the routing decision visible: name the tier per delegation in the plan
  (e.g. "Step 3: `terraform-manager-codex` — generate the module boilerplate").
- Never spawn a codex/ollama peer just because Claude is a little slow — the
  chain triggers on real limits + task fit, not impatience.
- If two managers on different tiers disagree on load-bearing content, surface
  the disagreement to the user — do NOT pick the higher-tier answer by default
  (an Ollama worker who ran a real command may be more grounded than Claude
  reasoning without one).

## Setup requirements

The chain is only real when the lower tiers are actually installed and running.
Run `.claude/scripts/fallback-setup.sh` to check readiness. What it verifies:

- Ollama service reachable at `localhost:11434`
- `codex` CLI on PATH
- `OPENAI_API_KEY` present in `~/.config/devops-tokens.env`

If any tier is missing, that tier is silently skipped and the chain uses
whatever remains. **Tier 1 (Claude) must always be present** — losing it is a
"stop and tell the user" event, not a graceful degradation.
