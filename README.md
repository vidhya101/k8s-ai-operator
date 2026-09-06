# Universal CI/CD + Kubernetes + Terraform Platform

One GitHub Actions pipeline, one Kubernetes manifest set (+ an operator), one Terraform root —
each parameterized by **cloud** (`aws | gcp | azure | local`) and, where relevant, **language**
(`python | node | react | java | go`) instead of forked per stack. Built to be copied into any
repository, in any company, and just work after a handful of variables are set.

```
scripts/wizard.sh        <- start here: asks cloud + language, scaffolds a target repo
.github/                 <- the CI/CD pipeline (reusable workflow + composite actions)
docker/templates/        <- one hardened multi-stage Dockerfile per language
k8s/app/                 <- Kustomize base + per-cloud overlays (the "hand-written" path)
k8s/operator/            <- a real Kubernetes operator (CRD + controller) — the "declarative" path
terraform/modules/       <- AWS / GCP / Azure network + managed-Kubernetes + workload-identity modules
terraform/platform/      <- three thin per-cloud roots (aws/ gcp/ azure/) calling terraform/modules/*
.claude/                 <- the DevOps/DevSecOps Claude Code agent+skill setup this was built with
```

## Quickstart

```bash
./scripts/wizard.sh
```

Answer two questions (cloud, language) and it copies the pipeline, a matching Dockerfile, and the
right Kubernetes overlay into your repo, then prints the exact repo Variables to set and the exact
`terraform apply` command for the cluster it deploys to. Nothing it prints runs automatically —
every apply/deploy step is something you run and review yourself (see `.claude/rules/safety.md`).

## The two ways to run a workload

**1. Hand-written Kustomize** (`k8s/app/base` + `k8s/app/overlays/<cloud>`) — a Deployment,
Service, HPA, PodDisruptionBudget, NetworkPolicy (default-deny + explicit allows), ResourceQuota,
LimitRange, and Ingress, all hardened by default: non-root, read-only root filesystem, all
capabilities dropped, seccomp `RuntimeDefault`, startup/liveness/readiness probes, topology spread
across zones+hosts, pod anti-affinity, and a `sleep`-based `preStop` hook for graceful shutdown —
with a per-cloud overlay only patching what's genuinely cloud-specific (IRSA / Workload Identity /
AAD annotation, ingress class, the ingress-controller's namespace for NetworkPolicy). Apply with:

```bash
kustomize build k8s/app/overlays/aws | kubectl apply -f -   # or gcp / azure / local
```

**2. The operator** (`k8s/operator/`) — apply one `AppWorkload` custom resource and a controller
(controller-runtime, Go) reconciles it into the same Deployment/Service/ServiceAccount/HPA/PDB
shape. The controller never branches on cloud or language — it only knows "run this
already-built, already-signed image, this many replicas, with these annotations." See
`k8s/operator/config/samples/platform_v1alpha1_appworkload.yaml`.

```bash
cd k8s/operator && make deploy            # installs the operator itself
kubectl apply -f config/samples/platform_v1alpha1_appworkload.yaml
```

Pick whichever fits your team: Kustomize if platform and app teams both need to read/patch raw
YAML; the operator if you'd rather offer app teams one 20-line CR and hide the object graph behind
it.

## The pipeline

`.github/workflows/ci-cd.yml` is the only file a consuming repo edits (usually not at all — see
Quickstart). It calls `.github/workflows/reusable-ci-cd.yml`, which runs, per push/PR:

`detect stack` → `security scan` (gitleaks + Trivy fs + Semgrep) → `build & test` → `build, scan,
sign & push image` (Buildx multi-arch, Trivy image scan, Syft SBOM, keyless Cosign sign+attest) →
`deploy` (Kustomize overlay for the target cloud, `kubectl rollout status` gate) — each cloud's
registry/cluster auth goes through OIDC (`aws-actions/configure-aws-credentials`,
`google-github-actions/auth`, `azure/login`), never a long-lived static credential.

Language is auto-detected from the repo's own manifests (`pom.xml`/`go.mod`/`package.json`/
`requirements.txt`) if not pinned explicitly — see `.github/actions/detect-stack`.

## Terraform

`terraform/platform/{aws,gcp,azure}` are three thin root configs, one per cloud, each calling only
`terraform/modules/<that-cloud>/...` — deliberately **not** one root with a `cloud_provider`
variable and conditional `count`. That was the first design here, and testing it with a real
`terraform plan` (not just `validate`) surfaced the actual failure mode: Terraform configures
every `provider` block declared anywhere in the module tree regardless of whether any resource
instance ends up using it, so a single root declaring `aws`+`google`+`azurerm` demanded GCP/Azure
credentials even when `cloud_provider = "aws"`. Three per-cloud roots are the honest fix — `cd` into
the one matching your cloud and nothing else is ever touched. `local` needs no Terraform at all —
use `kind`/`k3d` directly.

```bash
cd terraform/platform/aws        # or gcp / azure
cp ../examples/aws.tfvars.example ./aws.auto.tfvars   # fill in the CHANGE_ME values
terraform init
terraform plan
terraform apply                  # only after reviewing the plan
```

Each cloud pair provisions a private-by-default VPC/VNet + managed Kubernetes cluster (EKS/GKE/AKS)
with Workload Identity federation wired up (`modules/aws/irsa`, `modules/azure/workload-identity`,
GKE's built-in Workload Identity) — the same identity model the `k8s/app/overlays/<cloud>`
ServiceAccount annotations expect.

State backend is intentionally **not** pre-selected: no Terraform configuration can pick a backend
*type* (local/s3/gcs/azurerm) from a variable — see the comment block in each
`terraform/platform/<cloud>/versions.tf` for the one-line edit +
`backend-configs/<cloud>.backend.hcl` pairing to move off local state.

## Security posture, in one place

- **Supply chain**: every image is Trivy-scanned (fs pre-build, image post-build), SBOM'd (Syft,
  SPDX), and signed + attested keylessly (Cosign, OIDC — no stored signing key).
- **Secrets**: gitleaks gates every pipeline run; nothing in this repo ever holds a real secret
  value (`.claude/rules/secrets.md`) — Kubernetes Secrets come from External Secrets Operator /
  the cloud's own secret manager, referenced, never inlined.
- **Identity**: OIDC everywhere — GitHub Actions to cloud (no stored cloud keys), Pod to cloud API
  (IRSA / Workload Identity / AAD Workload Identity, no downloaded service-account keys).
  `automountServiceAccountToken: false` on every app pod that doesn't call the Kubernetes API.
- **Runtime**: non-root, read-only root filesystem, all Linux capabilities dropped, seccomp
  `RuntimeDefault`, default-deny `NetworkPolicy` with explicit allows, namespace `ResourceQuota` +
  `LimitRange` so one workload can't starve a shared namespace/cluster.
- **Change safety**: nothing in this repo runs `terraform apply`, `kubectl apply`, or a cloud
  mutation on its own — see `.claude/rules/safety.md`, which every agent working in this repo
  follows.

## Extending it

- **New language**: add `docker/templates/<lang>.Dockerfile` and a `case` branch in
  `.github/actions/build-test/action.yml` + `.github/actions/detect-stack/action.yml`. Nothing else
  changes — the reusable workflow, the Kubernetes manifests, and Terraform don't know or care what
  language the image was built from.
- **New cloud**: add `terraform/modules/<cloud>/{network,<k8s-service>}`, a
  `k8s/app/overlays/<cloud>`, and a cloud branch in `.github/actions/{build-push-image,deploy-k8s}`.
  Same shape as the three that exist — copy the closest one and adjust the provider calls.
