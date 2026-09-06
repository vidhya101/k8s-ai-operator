---
name: mlops
description: MLOps discipline — reproducible training, model versioning/registries, and safe serving/rollback. Use for ML pipeline design questions; see the mlops-reviewer agent for a structured review of an existing pipeline.
---

# MLOps

Applying DevOps discipline (versioning, CI/CD, observability) to the ML lifecycle: data → training →
model → serving. See the `mlops-reviewer` agent for a structured pipeline review.

## Reproducibility

- A specific model version should be traceable back to: the exact code commit, the exact dataset
  snapshot/version, the exact hyperparameters, and the exact dependency versions used to train it —
  "the same data" needs to mean an immutable, referenceable snapshot, not "whatever's in the table now."
- Experiment tracking (MLflow, Weights & Biases, or equivalent) captures this lineage automatically per
  run — relying on manual notes/spreadsheets doesn't scale and loses information.

## Model Registry & Promotion

- Trained models are versioned artifacts with metadata (lineage, evaluation metrics, training date) in a
  registry — not files dropped in a bucket with no tracked provenance.
- A promotion path: newly trained model → offline evaluation against a held-out set → staging/shadow
  deployment (serving real traffic but not affecting user-facing decisions, or a canary slice) →
  production promotion — with a rollback to the previous production model that's actually been exercised,
  not just theoretically possible.

## Serving & Monitoring

- Train/serve skew: the feature computation logic used at inference must match what was used at
  training time — a common, hard-to-detect source of production model degradation when the two are
  implemented separately (e.g. a batch training pipeline and a real-time serving path with duplicated logic).
- Drift monitoring: track input feature distribution and prediction quality/business-outcome metrics in
  production, with a defined action when drift crosses a threshold (alert, automatic retrain trigger,
  fallback to a simpler/previous model).
- Data quality gates before training: schema validation, null-rate/distribution sanity checks on the
  training set — a training run on corrupted upstream data produces a confidently-wrong model, which is
  worse than an obviously-broken one.

## Common Pitfalls

- No rollback path from a bad production model — the registry has versions, but nothing actually
  exercises reverting to one under pressure until it's needed for the first time during an incident.
- Feature engineering logic duplicated (not shared) between the training pipeline and the serving path,
  drifting apart silently over time.
- PII/sensitive data in training sets handled without an explicit stated data-governance policy — ask
  rather than assume the compliance posture (per `CLAUDE.md` Section 1.1).
- Model performance monitored only via the training-time offline metric, with no production monitoring
  of the metric that actually matters to the business.
