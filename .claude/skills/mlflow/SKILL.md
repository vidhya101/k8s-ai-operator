---
name: mlflow
description: MLflow — experiment tracking, model registry, and reproducible run lineage. Use when instrumenting training runs, managing model versions/stages, or debugging why a run isn't reproducible.
---

# MLflow

Experiment tracking and model registry — the piece that makes "which code + data + params produced this
model" an answered question instead of tribal knowledge (see the `mlops` skill for the discipline this
serves).

## Tracking

```python
import mlflow

mlflow.set_experiment("my-experiment")
with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.94)
    mlflow.log_artifact("confusion_matrix.png")
    mlflow.sklearn.log_model(model, "model")   # framework-specific autologging also available
```

- Log parameters, metrics, and artifacts for every run — not just the final model file. A run with only
  the model artifact and no logged params/metrics/data-version is not reproducible, just archived.
- `mlflow.autolog()` covers many frameworks' common metrics/params automatically — use it as a floor, add
  explicit logging for anything domain-specific it doesn't capture.

## Model Registry

```python
mlflow.register_model("runs:/<run_id>/model", "my-model")
```

```bash
mlflow models serve -m "models:/my-model/Production" -p 5000     # local serving for testing
mlflow gc                                                          # permanently delete soft-deleted runs
```

- Registered models progress through stages (`Staging`, `Production`, `Archived`) — promotion should be a
  deliberate action after evaluation, not automatic on every training run.
- The registry entry links back to the run that produced it — verify this linkage is intact rather than
  registering a model artifact detached from its originating run's logged lineage.

## Key Commands

```bash
mlflow server --backend-store-uri <db-uri> --default-artifact-root <artifact-store>   # tracking server
mlflow experiments search
mlflow runs list --experiment-id <id>
mlflow runs describe --run-id <id>
```

## Common Pitfalls

- Tracking server's backend store (metadata) and artifact store (model files) pointed at ephemeral/local
  storage in a shared environment — metadata or artifacts vanish on pod restart if not backed by a
  persistent DB and object store respectively.
- `mlflow gc` run without confirming which runs are being permanently deleted — this is destructive and
  irreversible, treat it with the same caution as any other destructive command (`.claude/rules/safety.md`).
- A model promoted to `Production` stage without a documented evaluation gate — the registry enables
  staged promotion, but doesn't enforce that a human/automated check actually happened before promoting.
- Autologging assumed to capture everything relevant for a custom training loop that doesn't go through
  the framework's standard `fit()`/`train()` entrypoint — verify what autolog actually captured.
