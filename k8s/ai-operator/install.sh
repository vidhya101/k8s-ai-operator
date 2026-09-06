#!/usr/bin/env bash
# ai-operator — one-command install. Idempotent: re-run to upgrade.
#
#   cp env.template .env && $EDITOR .env
#   ./install.sh                 # interactive (confirms the target cluster + each mutating step)
#   ./install.sh --yes           # non-interactive (CI)
#   ./install.sh --uninstall     # remove the operator (keeps memory PVC unless --purge)
#
# What it does:
#   1. installs missing prereqs (kubectl, helm, kustomize, istioctl, jq, docker/ollama)
#   2. confirms which cluster you're pointing at
#   3. verifies local Ollama + pulls the models the agents need
#   4. installs cluster prereqs (Kyverno — required for the guardrails; metrics-server if absent)
#   5. builds the operator image and gets it to the cluster (registry push or kind/minikube load)
#   6. applies CRDs + RBAC + the operator, wired to your Ollama and Git
set -Eeuo pipefail
cd "$(dirname "$0")"

YES=0; UNINSTALL=0; PURGE=0
for a in "$@"; do case "$a" in
  --yes|-y) YES=1;; --uninstall) UNINSTALL=1;; --purge) PURGE=1;;
  -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
esac; done

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
confirm() { [ "$YES" = 1 ] && return 0; read -r -p "    $1 [y/N] " r; [ "$r" = y ] || [ "$r" = Y ]; }
have() { command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"; ARCH="$(uname -m)"; [ "$ARCH" = x86_64 ] && ARCH=amd64; [ "$ARCH" = aarch64 ] && ARCH=arm64

[ -f .env ] || die "no .env — run: cp env.template .env && \$EDITOR .env"
set -a; . ./.env; set +a
: "${OLLAMA_IP:?set OLLAMA_IP in .env}"; : "${OLLAMA_PORT:=11434}"; : "${IMAGE_TAG:=v0.1.0}"
: "${MODE:=observe}"; : "${GIT_BRANCH_BASE:=main}"

# ---------------------------------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------------------------------
if [ "$UNINSTALL" = 1 ]; then
  say "Removing ai-operator (Deployment, RBAC, CRDs). Findings/Remediations go with the CRDs."
  confirm "proceed?" || exit 0
  kubectl delete -k deploy/ --ignore-not-found || true
  kubectl delete -f crds/ --ignore-not-found || true
  if [ "$PURGE" = 1 ]; then
    warn "purging memory PVC + backups"
    kubectl -n ai-operator delete pvc ai-operator-memory --ignore-not-found || true
    kubectl -n ai-operator delete cm -l ai-operator.io/backup=true --ignore-not-found || true
  else
    say "memory PVC kept. Re-run install to reconnect, or --purge to delete it."
  fi
  exit 0
fi

# ---------------------------------------------------------------------------------------------------
# 1. local prereqs
# ---------------------------------------------------------------------------------------------------
say "Checking local tools"
pkg_install() { # $1 = tool
  case "$OS" in
    Darwin) have brew || die "install Homebrew first: https://brew.sh"; brew install "$1";;
    Linux)  warn "installing $1 ..."; return 1;;  # handled per-tool below
  esac
}
install_kubectl()  { curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/$( [ "$OS" = Darwin ] && echo darwin || echo linux )/$ARCH/kubectl"; sudo install -m755 /tmp/kubectl /usr/local/bin/kubectl; }
install_helm()     { curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash; }
install_kustomize(){ curl -fsSL "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash && sudo mv kustomize /usr/local/bin/; }
install_istioctl() { curl -fsSL https://istio.io/downloadIstioctl | sh - && sudo mv "$HOME/.istioctl/bin/istioctl" /usr/local/bin/ 2>/dev/null || true; }
install_jq()       { case "$OS" in Darwin) brew install jq;; Linux) sudo apt-get update -qq && sudo apt-get install -y jq || sudo yum install -y jq;; esac; }

for t in kubectl helm kustomize istioctl jq; do
  if have "$t"; then printf '    ✓ %s\n' "$t"; else
    warn "$t missing"
    confirm "install $t?" || die "$t is required"
    if [ "$OS" = Darwin ]; then brew install "$t" 2>/dev/null || "install_$t"; else "install_$t"; fi
  fi
done
have docker || have podman || warn "no docker/podman — needed only to build the image (skip if IMAGE_REPO is prebuilt)"

# ---------------------------------------------------------------------------------------------------
# 2. confirm the target cluster
# ---------------------------------------------------------------------------------------------------
have kubectl || die "kubectl not on PATH"
CTX="$(kubectl config current-context)"
DISTRO="$(bash scripts/detect-distro.sh || echo unknown)"
say "Target cluster"
printf '    context : %s\n    distro  : %s\n    server  : %s\n' \
  "$CTX" "$DISTRO" "$(kubectl version -o json 2>/dev/null | jq -r '.serverVersion.gitVersion' 2>/dev/null || echo '?')"
case "$CTX" in *prod*|*production*) warn "context name contains 'prod' — be sure.";; esac
confirm "install ai-operator into THIS cluster?" || die "aborted"

# ---------------------------------------------------------------------------------------------------
# 3. Ollama + models
# ---------------------------------------------------------------------------------------------------
say "Ollama"
LOCAL_OLLAMA="http://localhost:${OLLAMA_PORT}"
if ! curl -fsS "$LOCAL_OLLAMA/api/tags" >/dev/null 2>&1; then
  if have ollama; then
    warn "ollama installed but not serving — starting it in the background"
    (OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT} nohup ollama serve >/tmp/ollama.log 2>&1 &) ; sleep 3
  else
    warn "ollama not installed"
    confirm "install Ollama now?" || die "Ollama is required"
    if [ "$OS" = Darwin ]; then brew install ollama; (ollama serve >/tmp/ollama.log 2>&1 &); sleep 3
    else curl -fsSL https://ollama.com/install.sh | sh; fi
  fi
fi
curl -fsS "$LOCAL_OLLAMA/api/tags" >/dev/null || die "Ollama still unreachable at $LOCAL_OLLAMA"
# is it listening on all interfaces? the cluster needs to reach $OLLAMA_IP, not just localhost
if ! curl -fsS "http://${OLLAMA_IP}:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
  warn "Ollama is up on localhost but NOT reachable on ${OLLAMA_IP}:${OLLAMA_PORT} (which is what the"
  warn "cluster will use). Restart it bound to all interfaces:  OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT} ollama serve"
  warn "(systemd: add 'Environment=OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT}' to the ollama unit, then restart)"
  confirm "continue anyway (fix this before the operator can think)?" || exit 1
fi
OLLAMA_HOST="$LOCAL_OLLAMA" bash scripts/pull-models.sh deploy/config.yaml

# ---------------------------------------------------------------------------------------------------
# 4. cluster prereqs
# ---------------------------------------------------------------------------------------------------
say "Cluster prerequisites"
if ! kubectl get crd clusterpolicies.kyverno.io >/dev/null 2>&1; then
  warn "Kyverno not installed — it enforces the 'cannot delete / cannot escalate' guardrails."
  confirm "helm install Kyverno now?" || die "Kyverno is required for the safety guardrails"
  helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null 2>&1 || true
  helm repo update >/dev/null
  helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace --wait
fi
if ! kubectl top nodes >/dev/null 2>&1; then
  warn "metrics-server absent (efficiency findings need it)."
  if confirm "helm install metrics-server?"; then
    helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null 2>&1 || true
    helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
      --set 'args={--kubelet-insecure-tls}' --wait || warn "metrics-server install failed — continuing"
  fi
fi

# ---------------------------------------------------------------------------------------------------
# 5. build + ship the image
# ---------------------------------------------------------------------------------------------------
IMAGE="${IMAGE_REPO:+$IMAGE_REPO:}ai-operator:${IMAGE_TAG}"
[ -n "${IMAGE_REPO:-}" ] && IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"
say "Building image: $IMAGE"
BUILDER="$(have docker && echo docker || echo podman)"
$BUILDER build -t "$IMAGE" --build-arg TARGETARCH="$ARCH" .
if [ -n "${IMAGE_REPO:-}" ]; then
  say "Pushing $IMAGE"; $BUILDER push "$IMAGE"
else
  case "$DISTRO" in
    kind)      kind load docker-image "$IMAGE" --name "${CTX#kind-}";;
    minikube)  minikube image load "$IMAGE";;
    docker-desktop) : ;;  # shares the daemon
    *) warn "no IMAGE_REPO set and distro '$DISTRO' can't side-load — set IMAGE_REPO in .env";;
  esac
fi

# ---------------------------------------------------------------------------------------------------
# 6. apply
# ---------------------------------------------------------------------------------------------------
say "Applying CRDs"
kubectl apply -f crds/

say "Rendering manifests"
WORK="$(mktemp -d)"; cp -r . "$WORK/src"; rm -rf "$WORK/src/.git"
sed -i.bak "s#OLLAMA_IP_PLACEHOLDER#${OLLAMA_IP}#" "$WORK/src/deploy/ollama.yaml"
sed -i.bak "s#IMAGE_PLACEHOLDER#${IMAGE}#" "$WORK/src/deploy/deployment.yaml"
sed -i.bak "s#mode: \"observe\"#mode: \"${MODE}\"#" "$WORK/src/deploy/config.yaml"
rm -f "$WORK"/src/deploy/*.bak

kubectl create namespace ai-operator --dry-run=client -o yaml | kubectl apply -f -
if [ -n "${GIT_REPO_URL:-}" ]; then
  kubectl -n ai-operator create secret generic ai-operator-git \
    --from-literal=repoURL="${GIT_REPO_URL}" --from-literal=token="${GIT_TOKEN:-}" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

say "Deploying"
kubectl apply -k "$WORK/src"
rm -rf "$WORK"

say "Waiting for rollout"
kubectl -n ai-operator rollout status deploy/ai-operator --timeout=180s || warn "not ready yet — check logs"

cat <<EOF

$(say "Done.")
  mode          : ${MODE}   (observe = report only; change with:
                  kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"mode":"assist"}}')
  watch it      : kubectl -n ai-operator logs deploy/ai-operator -f
  findings      : kubectl -n ai-operator get findings
  remediations  : kubectl -n ai-operator get remediations
  what it learnt: kubectl -n ai-operator get cm agent-memory-digest -o yaml
  kill switch   : kubectl -n ai-operator patch cm ai-operator-config --type merge -p '{"data":{"paused":"true"}}'
EOF
