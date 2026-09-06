---
name: airflow
description: Apache Airflow — DAG authoring, scheduling, and operational debugging for data/ML pipeline orchestration. Use when writing or debugging an Airflow DAG, or reviewing scheduling/retry behavior.
---

# Airflow

DAG-based workflow orchestration, commonly the backbone for data pipelines (pair with the
`data-engineering-reviewer` agent) and can also orchestrate ML training pipelines as an alternative to
Kubeflow Pipelines.

## DAG Authoring

```python
from airflow.decorators import dag, task
from datetime import datetime

@dag(schedule="@daily", start_date=datetime(2024, 1, 1), catchup=False,
     default_args={"retries": 2, "retry_delay": 300})
def my_pipeline():
    @task
    def extract(): ...
    @task
    def transform(data): ...
    @task
    def load(data): ...

    load(transform(extract()))

my_pipeline()
```

## Core Principles

- **Idempotency**: a task re-run for the same `execution_date`/logical date should produce the same
  result, not duplicate/append — same principle as the `data-engineering-reviewer` agent's core focus.
  Use partition-overwrite/upsert patterns in the actual data write, not just retry-safety at the task level.
- **`catchup`**: `catchup=True` (the default in older Airflow) backfills every missed schedule interval
  since `start_date` on first deploy — often not what's intended; set explicitly rather than relying on
  the default, and know which behavior a given DAG needs.
- **Retries**: `retries`/`retry_delay` on tasks expected to hit transient failures (network calls,
  external API rate limits) — but retries don't fix a task that's deterministically failing; distinguish
  "will succeed on retry" from "will fail identically every time" before assuming more retries help.
- **Idempotent scheduling**: prefer the Airflow-native scheduler/DAG triggers over external cron jobs
  calling into Airflow — keeps dependency/backfill semantics in one place.

## Key Commands

```bash
airflow dags list
airflow dags list-runs -d <dag_id>
airflow tasks list <dag_id>
airflow dags trigger <dag_id>                        # manual run, mutating — confirm first
airflow tasks test <dag_id> <task_id> <execution_date>  # run a single task locally without the scheduler
airflow dags pause / unpause <dag_id>
```

## Common Pitfalls

- `catchup` left at its default without checking, causing an unexpected backfill storm (or a silent gap)
  on first deploy of a new DAG.
- Tasks with side effects (writes, API calls) that aren't idempotent, so a scheduler retry after a partial
  failure produces duplicate/corrupted output.
- Heavy computation done directly in the DAG file's top-level code (outside a task) — this code runs on
  every scheduler parse cycle (not just execution), which can slow down the whole scheduler if expensive.
- XComs (Airflow's inter-task data passing) used to pass large datasets directly instead of a reference
  (a path/URI to external storage) — XCom storage isn't designed for large payloads.
