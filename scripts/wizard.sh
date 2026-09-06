#!/usr/bin/env bash
# The "magic" wrapper: ask two questions (cloud, language), scaffold everything else.
#
# What it does, concretely:
#   1. Prompts for cloud (aws|gcp|azure|local) and language (python|node|react|java|go) — or
#      takes them as flags for non-interactive/CI use.
#   2. Copies .github/workflows/ci-cd.yml + .github/actions/* into the target repo (unchanged —
#      they're already cloud/language-agnostic; nothing to template).
#   3. Copies the matching docker/templates/<language>.Dockerfile to ./Dockerfile if the target
#      repo doesn't already have one (never overwrites an existing Dockerfile).
#   4. Copies k8s/app/{base,overlays/<cloud>} into the target repo's k8s/ directory.
#   5. Prints the exact repo Variables (Settings -> Secrets and variables -> Actions -> Variables)
#      the copied ci-cd.yml expects, and the exact `terraform apply` command (run from
#      terraform/platform/<cloud>, the per-cloud root config) for the matching cluster, so there's
#      no guessing after the scaffold runs.
#
# This script does not run `terraform apply`, `kubectl apply`, or any mutating cloud/cluster
# command itself — it only writes files and prints next steps. Per .claude/rules/safety.md, any
# apply/deploy always needs an explicit, reviewed run of its own.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$(pwd)"

CLOUD=""
LANGUAGE=""
APP_NAME=""
IMAGE_NAME=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [--cloud aws|gcp|azure|local] [--language python|node|react|java|go] \\
                         [--app-name NAME] [--image-name NAME] [--target-dir PATH]

Every flag is optional — anything not given is prompted for interactively. Run with no flags at
all for the fully interactive experience.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --cloud) CLOUD="$2"; shift 2 ;;
    --language) LANGUAGE="$2"; shift 2 ;;
    --app-name) APP_NAME="$2"; shift 2 ;;
    --image-name) IMAGE_NAME="$2"; shift 2 ;;
    --target-dir) TARGET_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage; exit 1 ;;
  esac
done

prompt_choice() {
  local var_name="$1" label="$2"; shift 2
  local options=("$@")
  local current="${!var_name}"
  if [ -n "$current" ]; then return; fi
  echo "$label"
  select opt in "${options[@]}"; do
    if [ -n "${opt:-}" ]; then printf -v "$var_name" '%s' "$opt"; break; fi
  done
}

prompt_text() {
  local var_name="$1" label="$2" default="${3:-}"
  local current="${!var_name}"
  if [ -n "$current" ]; then return; fi
  read -r -p "$label${default:+ [$default]}: " value
  printf -v "$var_name" '%s' "${value:-$default}"
}

echo "=== Universal CI/CD + Kubernetes + Terraform scaffold ==="
prompt_choice CLOUD    "Target cloud:"    aws gcp azure local
prompt_choice LANGUAGE "Application language:" python node react java go
prompt_text   APP_NAME   "Application name (used as k8s object name + terraform 'name')" "my-app"
prompt_text   IMAGE_NAME "Container image name" "$APP_NAME"

echo
echo "-> cloud=$CLOUD  language=$LANGUAGE  app-name=$APP_NAME  image-name=$IMAGE_NAME"
echo "-> scaffolding into: $TARGET_DIR"
echo

# ---------------- 1. GitHub Actions ----------------
mkdir -p "$TARGET_DIR/.github/workflows" "$TARGET_DIR/.github/actions"
cp -n "$REPO_ROOT/.github/workflows/ci-cd.yml" "$TARGET_DIR/.github/workflows/ci-cd.yml" 2>/dev/null || \
  cp "$REPO_ROOT/.github/workflows/ci-cd.yml" "$TARGET_DIR/.github/workflows/ci-cd.yml"
cp -n "$REPO_ROOT/.github/workflows/reusable-ci-cd.yml" "$TARGET_DIR/.github/workflows/reusable-ci-cd.yml" 2>/dev/null || \
  cp "$REPO_ROOT/.github/workflows/reusable-ci-cd.yml" "$TARGET_DIR/.github/workflows/reusable-ci-cd.yml"
cp -r "$REPO_ROOT/.github/actions/." "$TARGET_DIR/.github/actions/"
echo "[ok] .github/workflows + .github/actions copied"

# ---------------- 2. Dockerfile ----------------
if [ -f "$TARGET_DIR/Dockerfile" ]; then
  echo "[skip] Dockerfile already exists in target repo — not overwriting"
else
  cp "$REPO_ROOT/docker/templates/${LANGUAGE}.Dockerfile" "$TARGET_DIR/Dockerfile"
  [ -f "$REPO_ROOT/docker/templates/nginx.react.conf" ] && [ "$LANGUAGE" = "react" ] && \
    cp "$REPO_ROOT/docker/templates/nginx.react.conf" "$TARGET_DIR/nginx.react.conf"
  echo "[ok] Dockerfile ($LANGUAGE template) written"
fi

# ---------------- 3. Kubernetes (Kustomize base + the chosen cloud's overlay) ----------------
mkdir -p "$TARGET_DIR/k8s/app"
cp -r "$REPO_ROOT/k8s/app/base" "$TARGET_DIR/k8s/app/base"
mkdir -p "$TARGET_DIR/k8s/app/overlays"
cp -r "$REPO_ROOT/k8s/app/overlays/$CLOUD" "$TARGET_DIR/k8s/app/overlays/$CLOUD"
# Stamp the real app/image name into the copied manifests (base uses generic "app"/APP_IMAGE).
grep -rl '\bapp\b' "$TARGET_DIR/k8s/app" >/dev/null 2>&1 && \
  find "$TARGET_DIR/k8s/app" -type f -name '*.yaml' -exec sed -i.bak \
    -e "s/name: app$/name: ${APP_NAME}/" \
    -e "s/app.kubernetes.io\/name: app$/app.kubernetes.io\/name: ${APP_NAME}/" \
    {} \; 2>/dev/null || true
find "$TARGET_DIR/k8s/app" -name '*.bak' -delete
echo "[ok] k8s/app/base + k8s/app/overlays/$CLOUD copied and stamped with name=$APP_NAME"

# ---------------- 4. Next steps ----------------
cat <<EOF

=== Scaffold complete. Two things left, both deliberate/manual by design (safety.md): ===

1. Set these repo Variables (Settings -> Secrets and variables -> Actions -> Variables) so
   .github/workflows/ci-cd.yml knows where to build/deploy:

     CLOUD_PROVIDER=$CLOUD
     APP_NAME=$APP_NAME
     IMAGE_NAME=$IMAGE_NAME
     DEFAULT_ENVIRONMENT=dev
EOF

case "$CLOUD" in
  aws)   echo "     AWS_REGION=... AWS_ACCOUNT_ID=... AWS_ROLE_TO_ASSUME=... EKS_CLUSTER_NAME=..." ;;
  gcp)   echo "     GCP_REGION=... GCP_PROJECT_ID=... GCP_WORKLOAD_IDENTITY_PROVIDER=... GCP_SERVICE_ACCOUNT=... GKE_CLUSTER_NAME=..." ;;
  azure) echo "     AZURE_CLIENT_ID=... AZURE_TENANT_ID=... AZURE_SUBSCRIPTION_ID=... AZURE_ACR_NAME=... AKS_RESOURCE_GROUP=... AKS_CLUSTER_NAME=..." ;;
  local) echo "     (set repo secret KUBECONFIG_CONTENT if the runner doesn't already have cluster access)" ;;
esac

if [ "$CLOUD" = "local" ]; then
  cat <<EOF

2. Bring up a local cluster (no Terraform involved for "local" — nothing to provision):

     kind create cluster --name $APP_NAME
     # or: k3d cluster create $APP_NAME
     kustomize build k8s/app/overlays/local | kubectl apply -f -

Push to main and the pipeline builds, scans, signs, and deploys $APP_NAME. That's it.
EOF
else
  cat <<EOF

2. Provision the cluster this pipeline deploys to (review the plan before applying — see
   .claude/rules/safety.md). Each cloud is its own root config, so this only ever needs $CLOUD
   credentials — nothing else is touched:

     cd $REPO_ROOT/terraform/platform/$CLOUD
     cp ../examples/${CLOUD}.tfvars.example ./${CLOUD}.auto.tfvars   # then edit the CHANGE_ME values
     terraform init
     terraform plan
     terraform apply   # only after reviewing the plan

Push to main and the pipeline builds, scans, signs, and deploys $APP_NAME to $CLOUD. That's it.
EOF
fi
