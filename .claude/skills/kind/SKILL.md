---
name: kind
description: KIND (Kubernetes IN Docker) — ephemeral local/CI Kubernetes clusters for testing manifests, Helm charts, and GitOps flows before they reach a real cluster. Use when setting up local development clusters or pre-deployment validation, distinct from kubeadm's production-cluster concerns.
---

# KIND (Kubernetes IN Docker)

Runs a real Kubernetes cluster inside Docker containers-as-nodes — fast to create/destroy, ideal for
local development and CI validation. Distinct from `kubeadm` (production, persistent, HA-focused) — KIND
clusters are meant to be ephemeral and disposable, not a lightweight production distro.

## Core Use Cases

- **Local development**: a real cluster to test manifests/Helm charts against without needing cloud
  credentials or a shared cluster — catches YAML/API errors and basic scheduling issues before anything
  reaches a shared environment.
- **CI validation**: spin up a KIND cluster inside a CI job, apply manifests, run smoke tests, tear down —
  gives CI a real Kubernetes API to validate against (`kubectl apply --dry-run=server` catches some
  issues, but a real applied-and-running check catches more) without needing a persistent test cluster.
- **Pre-production GitOps validation**: apply the same ArgoCD Application/Helm chart against a KIND
  cluster as a pre-flight check before it reaches a real environment — catches configuration errors that
  would otherwise only surface once ArgoCD syncs against the real target.

## Basic Usage

```bash
kind create cluster --name test-cluster
kind create cluster --name test --config kind-config.yaml   # multi-node, custom config

kubectl cluster-info --context kind-test-cluster
kind load docker-image my-app:local --name test-cluster       # load a locally-built image without
                                                                # needing to push to a registry first
kind delete cluster --name test-cluster
```

```yaml
# kind-config.yaml — multi-node cluster for testing scheduling/affinity behavior
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

## In CI

```yaml
# Example GitHub Actions step (see github-actions skill for full workflow context)
- uses: helm/kind-action@<pinned-sha>
  with: { cluster_name: test }
- run: kubectl apply -k overlays/test/ && kubectl wait --for=condition=available deployment/my-app --timeout=60s
```

## Common Pitfalls

- Treating KIND cluster behavior as fully representative of a cloud-managed cluster (EKS/AKS/GKE) —
  networking (CNI), storage classes, and Ingress controller behavior differ; KIND validates Kubernetes API
  correctness and basic scheduling, not cloud-specific integrations (IRSA, cloud load balancers) covered
  in the `eks`/`aks`/`gke` skills.
- `kind load docker-image` forgotten, so a locally-built image reference resolves to `ImagePullBackOff`
  inside the KIND cluster (it has no access to a local Docker daemon's image cache by default — the image
  must be explicitly loaded in).
- KIND clusters left running/accumulating in a CI environment or locally, consuming resources — always
  pair `create` with a corresponding teardown, especially in CI where a leaked cluster from a previous run
  isn't cleaned up automatically.
- Using KIND for something that's actually testing production-scale behavior (load testing, HA failover
  testing) — it's for functional/manifest validation, not a substitute for `chaos-engineering` or
  `load-testing` against a representative environment.
