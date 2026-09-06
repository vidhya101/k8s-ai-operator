---
name: feature-store
description: Feature stores (Feast) — standardizing ML feature definitions to guarantee train/serve consistency. Use when a project uses a feature store, or when diagnosing train/serve skew (a model that performs differently in production than offline evaluation suggested).
---

# Feature Store (Feast)

Solves a specific, high-impact MLOps failure mode: **train/serve skew** — where the feature computation
logic used during training differs from what's used at inference time, causing a model to behave
differently in production than offline evaluation predicted. See the `mlops` skill for where this fits
in the broader lifecycle, and `mlflow`/`kubeflow`/`kserve` for the surrounding training/serving pipeline.

## Core Concepts

- **Feature definitions**: declared once (a feature's source, transformation, and data type), consumed
  consistently by both the training pipeline (batch, historical feature retrieval) and the serving path
  (online, low-latency single-entity lookup) — the single-definition-two-consumption-paths model is what
  actually prevents skew, rather than relying on two independently-maintained implementations staying in sync.
- **Offline store**: historical feature values for training (typically backed by a data warehouse/lake —
  BigQuery, Snowflake, an Iceberg/Delta table, see `data-lakehouse` skill).
- **Online store**: low-latency key-value lookup for serving (Redis, DynamoDB, or similar) — populated by
  a materialization job that syncs from the offline store on a schedule.
- **Point-in-time correctness**: when retrieving historical features for training, the feature store
  fetches the value as it was *at the time of the labeled event*, not the current value — critical for
  avoiding label leakage (training on a feature value that wasn't actually available yet at prediction time).

## Example Shape (Feast)

```python
from feast import FeatureStore

store = FeatureStore(repo_path=".")

# Training: point-in-time-correct historical features for a set of labeled events
training_df = store.get_historical_features(
    entity_df=labels_df,          # includes entity keys + event timestamps
    features=["driver_stats:avg_daily_trips", "driver_stats:conv_rate"],
).to_df()

# Serving: low-latency online lookup for a single prediction request
online_features = store.get_online_features(
    features=["driver_stats:avg_daily_trips"],
    entity_rows=[{"driver_id": 1001}],
).to_dict()
```

## When It's Worth Introducing

- Multiple models/teams reusing the same underlying features, where duplicated feature logic has already
  caused (or is a real risk of causing) train/serve skew — the strongest justification.
- A single model with simple, already-consistent feature logic doesn't necessarily need a feature store —
  introducing one adds real infrastructure (offline + online store, materialization jobs) that isn't free;
  weigh it the same way as any other tooling addition (Section 1.2).

## Common Pitfalls

- Feature transformation logic duplicated outside the feature store for "just this one case" (a quick
  serving-side patch), reintroducing exactly the train/serve skew the feature store exists to prevent.
- Materialization job (offline → online sync) not running on a cadence that matches how fresh the serving
  path actually needs features to be — a stale online store serves outdated features with no obvious error.
- Point-in-time joins done manually/incorrectly elsewhere in a pipeline that bypasses the feature store for
  some features, reintroducing label leakage risk for those specific features.
- No feature versioning/lineage tracked, making it hard to know which feature definition version a given
  deployed model was actually trained against — pairs with `mlflow`'s run-lineage principle.
