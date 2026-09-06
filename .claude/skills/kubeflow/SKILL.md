---
name: kubeflow
description: Kubeflow — ML pipelines, notebooks, and training operators (TFJob/PyTorchJob) on Kubernetes. Use when the ML platform is Kubeflow; pair with kserve for serving and mlflow for experiment tracking/registry if used alongside it.
---

# Kubeflow

A collection of Kubernetes-native ML tooling: Pipelines (KFP), Notebooks, and training operators. Treat
each component as independently adoptable — a project may use only Pipelines without the full platform.

## Components

- **Kubeflow Pipelines (KFP)**: DAG-based ML workflow orchestration, defined in Python (`kfp` SDK),
  compiled to Argo Workflows under the hood, run via a `kfp.Client()` or the KFP UI.
- **Notebooks**: managed Jupyter/VS Code server pods with persistent storage, RBAC-scoped per user/namespace.
- **Training Operators** (`TFJob`, `PyTorchJob`, `MPIJob`, etc.): CRDs that run distributed training as a
  Kubernetes-native job, handling worker/parameter-server pod coordination.
- **Katib**: hyperparameter tuning/AutoML on top of the training operators.

## Pipeline Authoring (KFP)

```python
from kfp import dsl

@dsl.component
def train(data_path: str) -> str:
    ...

@dsl.pipeline(name="training-pipeline")
def pipeline(data_path: str = "gs://bucket/data"):
    train_task = train(data_path=data_path)
```

```bash
kfp dsl compile --py pipeline.py --output pipeline.yaml   # compile to Argo Workflow manifest
kfp run create --experiment-name exp1 --pipeline-file pipeline.yaml
kfp run list
```

## Key Principles

- Pipeline steps (components) should be idempotent and cacheable where possible — KFP's caching skips
  re-running a step whose inputs haven't changed, saving significant compute on iteration.
- Resource requests/limits on every pipeline step's underlying pod, same discipline as any Kubernetes
  workload (see `kubernetes` skill) — a training step with no memory limit can OOM-kill the node it lands on.
- Distributed training jobs (`PyTorchJob`, `TFJob`) need their worker count and resource requests sized
  against actual cluster capacity — a job requesting more GPU workers than the cluster can schedule sits
  `Pending` indefinitely with no obvious error.
- Namespace-per-user/team (Kubeflow's Profile CRD) for multi-tenancy — don't run all teams' notebooks and
  pipelines in one shared namespace without a reason.

## Common Pitfalls

- Pipeline components with no caching key sensitivity, so every run re-executes every step even when
  inputs are unchanged — wastes compute on iteration.
- Notebook servers left running indefinitely, holding GPU/resource allocations no one is actively using —
  worth a culling policy or idle-timeout if the platform doesn't already enforce one.
- Training operator CRDs applied without checking actual available GPU/node capacity first, leading to
  pods stuck `Pending` that look like a bug but are a scheduling/capacity issue.
