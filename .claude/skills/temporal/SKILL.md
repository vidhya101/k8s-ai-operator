---
name: temporal
description: Temporal — durable workflow orchestration for long-running, stateful business processes with automatic retry/replay, distinct from Airflow's DAG-scheduling model. Use when a workflow needs to survive process crashes/deploys mid-execution, hold state for days/months, or coordinate complex human-in-the-loop steps.
---

# Temporal (Durable Workflow Orchestration)

Solves a different problem than `airflow`: Airflow schedules and runs DAGs of typically-short tasks on a
recurring basis; Temporal keeps a **workflow's execution state durable** across crashes, deploys, and
arbitrarily long real-world time (a workflow can run for months, survive the worker process restarting
entirely) — suited to business processes (an order fulfillment saga, a multi-step approval flow, a
long-running deployment orchestration) more than scheduled batch/data pipelines.

## Core Model

- **Workflow**: the orchestration logic, written as ordinary code (not YAML/DAG config) — Temporal
  deterministically replays this code from its event history to reconstruct state after any interruption,
  which is what makes "durable" true even through a worker crash mid-execution.
- **Activity**: the actual side-effecting work (an API call, a database write) — activities can fail and
  retry independently per their own retry policy, while the surrounding workflow logic stays consistent.
- **Determinism requirement**: workflow code must be deterministic (no direct random numbers, no direct
  system time, no direct network calls — those belong in activities) because Temporal replays it from
  history; non-deterministic workflow code is the most common category of subtle Temporal bug.

```python
@workflow.defn
class OrderFulfillment:
    @workflow.run
    async def run(self, order_id: str) -> str:
        await workflow.execute_activity(charge_payment, order_id, start_to_close_timeout=timedelta(minutes=5))
        await workflow.execute_activity(ship_order, order_id, start_to_close_timeout=timedelta(hours=1))
        return "completed"
```

## Why Durability Matters Here

- If the worker process crashes mid-workflow (deploy, OOM, node failure), Temporal replays the event
  history on another worker and resumes exactly where it left off — no manual "what step were we on"
  recovery logic needed in application code, which is the core value proposition versus hand-rolling this
  with a database-backed state machine.
- Retry policies, timeouts, and (for signals/queries) human-in-the-loop waiting are first-class, not
  bolted on — a workflow can `await` a signal (e.g. "wait for manager approval") for days without
  consuming worker resources while waiting.

## Common Pitfalls

- Non-deterministic code inside workflow logic (calling an external API directly, using `random()`
  or `time.now()` outside an activity) — breaks replay and causes hard-to-diagnose workflow failures,
  usually only surfacing after a worker restart forces a replay.
- Activities with no timeout/retry policy configured, relying on defaults that may not match the actual
  operation's expected duration/failure characteristics.
- Using Temporal for what's actually a simple scheduled batch job — `airflow`/`cron-scheduling` are the
  simpler, more appropriate tool when there's no need for long-lived state or crash-durable execution;
  Temporal's model is more powerful and also more operationally involved than needed for that case.
- Large payloads passed directly through workflow/activity arguments instead of a reference (same "claim
  check" pattern `aws-serverless` describes for SQS) — Temporal's event history has practical size limits.
