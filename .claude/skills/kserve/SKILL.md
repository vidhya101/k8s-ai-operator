---
name: kserve
description: KServe — Kubernetes-native model serving via the InferenceService CRD, including canary rollouts and autoscaling to zero. Use when deploying/debugging a model-serving endpoint on Kubernetes.
---

# KServe

Standardizes model serving on Kubernetes behind a single CRD (`InferenceService`), across frameworks
(TensorFlow, PyTorch, SKLearn, XGBoost, and custom containers) with built-in autoscaling, canary rollout,
and request/response logging.

## InferenceService

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: my-model
spec:
  predictor:
    model:
      modelFormat: { name: sklearn }
      storageUri: "s3://my-bucket/models/my-model/"
      resources:
        requests: { cpu: "1", memory: "1Gi" }
        limits: { cpu: "2", memory: "2Gi" }
    minReplicas: 1        # 0 enables scale-to-zero (cold-start latency tradeoff)
    maxReplicas: 5
  # Canary rollout: split traffic between the current and a new model revision
  # by applying a new spec with `canaryTrafficPercent` set on the predictor.
```

## Core Concepts

- **Predictor**: the model server itself; KServe provides pre-built runtimes per framework, or a custom
  container implementing the KServe V2 inference protocol.
- **Transformer** (optional): pre/post-processing logic run as a separate pod in front of the predictor —
  keeps feature transformation logic out of the model-serving container.
- **Explainer** (optional): serves model explanations (e.g. via Alibi) alongside predictions.
- **Scale-to-zero**: `minReplicas: 0` fully deallocates compute when idle, at the cost of cold-start
  latency on the next request — appropriate for low-traffic/bursty endpoints, not for latency-sensitive
  always-on services.
- **Canary rollout**: shifting a percentage of traffic to a new model revision before full cutover, the
  same principle as a canary application deployment, applied to model versions specifically.

## Key Commands

```bash
kubectl get inferenceservice -n <ns>
kubectl describe inferenceservice <name> -n <ns>
kubectl get inferenceservice <name> -n <ns> -o jsonpath='{.status.url}'
curl -H "Host: <name>.<ns>.example.com" http://<ingress-ip>/v1/models/<name>:predict -d @input.json
```

## Common Pitfalls

- `storageUri` pointing at a model artifact the serving pod's ServiceAccount doesn't have read access to
  (cloud storage IAM/Workload Identity misconfiguration) — manifests as the pod stuck in an init/loading
  state, not an obvious permission error.
- Scale-to-zero enabled for a latency-sensitive endpoint without the team understanding the cold-start
  cost — first request after idle can be seconds slower than steady-state.
- No canary step before full traffic cutover to a new model version — a regressed model reaches 100% of
  traffic immediately instead of being caught on a small percentage first.
- Resource limits sized for the model's steady-state memory but not its (often much higher) peak load
  time, causing OOMKills under batch/burst traffic.
