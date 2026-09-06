---
name: sagemaker
description: AWS SageMaker — managed training jobs, model endpoints, and pipelines. Use when the ML platform is AWS-native SageMaker rather than (or alongside) Kubeflow/KServe/MLflow.
---

# AWS SageMaker

AWS's managed ML platform — covers the same training/serving/pipeline territory as `kubeflow`/`kserve`/
`mlflow`, but as a fully-managed AWS service rather than Kubernetes-native tooling. Check which a given
project actually uses before assuming Kubernetes-based ML tooling applies.

## Training

- Managed training jobs run on ephemeral, right-sized compute (including spot instances via managed spot
  training, meaningfully cheaper for interruption-tolerant training runs) — SageMaker handles checkpoint/
  resume on spot interruption if the training script supports it; a script with no checkpointing loses
  progress on interruption regardless of SageMaker's spot handling.
- Distributed training (data-parallel or model-parallel) via SageMaker's distributed training libraries —
  conceptually the same problem `kubeflow`'s training operators (`PyTorchJob`/`TFJob`) solve, different
  implementation.
- Experiment tracking via SageMaker Experiments, or bring your own (MLflow) — check which a project uses;
  don't assume SageMaker Experiments is in use just because SageMaker is the training platform.

## Model Registry & Endpoints

- **SageMaker Model Registry**: versioned model artifacts with approval status (`PendingManualApproval`,
  `Approved`, `Rejected`) — the SageMaker-native equivalent of MLflow's model registry stages.
- **Real-time endpoints**: persistent, auto-scaling inference endpoints — the SageMaker-native equivalent
  of `kserve`'s `InferenceService`; supports multi-model endpoints (many models sharing one endpoint's
  compute) and multi-variant endpoints (for A/B testing / canary rollout between model versions).
- **Serverless inference / Async inference**: for bursty or long-running inference workloads respectively,
  avoiding the cost of an always-on real-time endpoint for traffic that doesn't need it — same "don't
  pay for idle capacity" principle as `kserve`'s scale-to-zero.
- **Batch Transform**: for offline, non-latency-sensitive bulk inference — don't stand up a real-time
  endpoint for a workload that's actually a batch job.

## Pipelines

- SageMaker Pipelines defines the same kind of DAG-based ML workflow as Kubeflow Pipelines
  (preprocessing → training → evaluation → conditional registration) but as a SageMaker-native construct
  — step caching works similarly (skip a step whose inputs/code haven't changed), same cost-saving logic
  as `kubeflow`'s KFP caching.

## Common Pitfalls

- A real-time endpoint left running for a workload that's actually infrequent/bursty — Serverless
  Inference or Batch Transform would be cheaper with no code change to the model itself.
- Training script with no checkpointing run on managed spot training, losing all progress on an
  interruption that spot training was supposed to make cheap, not lossy.
- IAM execution role for a training job or endpoint scoped broader than the specific S3 prefixes/other
  resources it actually needs — same least-privilege principle as any other AWS execution role.
- Model promoted to an endpoint with no evaluation gate recorded in the Model Registry's approval
  workflow — same "no documented promotion gate" gap the `mlflow` skill flags for its own registry.
