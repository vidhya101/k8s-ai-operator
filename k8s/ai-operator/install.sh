#!/usr/bin/env bash
# ai-operator installer — deploys into your EXISTING Kubernetes cluster.
# No image build, no registry, no host networking.
#
#   ./install.sh                 # install into the cluster your current kubeconfig points at
#                                #   - laptop:  `kubectl get nodes` must already work
#                                #   - control-plane node:  run as-is (uses admin.conf) or `sudo ./install.sh`
#   ./install.sh --kind          # NO cluster yet? spin up a throwaway local one to try it
#   ./install.sh --yes           # no prompts (CI)
#   ./install.sh --uninstall     # remove the operator (keeps memory/models PVCs unless --purge)
#
#   cp env.template .env         # OPTIONAL — every setting has a working default
#
# Host needs: kubectl. (helm only if you opt into Kyverno; kind + docker only for --kind.)
set -Eeuo pipefail
cd "$(dirname "$0")"

# ---- args ---------------------------------------------------------------------------------------
YES=0 KIND=0 UNINSTALL=0 PURGE=0
for a in "$@"; do case "$a" in
  -y|--yes) YES=1;; --kind) KIND=1;; --uninstall) UNINSTALL=1;; --purge) PURGE=1;;
  -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  *) echo "unknown arg: $a" >&2; exit 2;;
esac; done

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
ask()  { [ "$YES" = 1 ] && return 0; printf '    %s [y/N] ' "$1"; read -r r; [ "$r" = y ] || [ "$r" = Y ]; }
have() { command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"; ARCH="$(uname -m)"; case "$ARCH" in x86_64) ARCH=amd64;; arm64|aarch64) ARCH=arm64;; esac
NS=ai-operator

# ---- .env (parsed line by line — never sourced) -----------------------------------------------
declare -A ENVV
if [ -f .env ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in ''|\#*) continue;; esac
    [ "${line#*=}" != "$line" ] || continue          # must contain '='
    k="${line%%=*}"; v="${line#*=}"
    k="$(printf '%s' "$k" | tr -d '[:space:]')"
    case "$k" in *[!A-Za-z0-9_]*|'') continue;; esac  # valid identifier only
    v="${v%%#*}"                                       # strip trailing comment
    v="$(printf '%s' "$v" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    v="${v#\"}"; v="${v%\"}"; v="${v#\'}"; v="${v%\'}"
    ENVV[$k]="$v"
  done < .env
fi
env_get() { printf '%s' "${ENVV[$1]:-${2:-}}"; }
MODE="$(env_get MODE observe)"
OLLAMA_EXTERNAL_URL="$(env_get OLLAMA_EXTERNAL_URL)"
GIT_REPO_URL="$(env_get GIT_REPO_URL)"
GIT_TOKEN="$(env_get GIT_TOKEN)"
SRC_REPO="$(env_get SRC_REPO https://github.com/vidhya101/k8s-ai-operator.git)"
SRC_REF="$(env_get SRC_REF main)"

# ---- tool install helpers --------------------------------------------------------------------
brew_or() { if [ "$OS" = Darwin ] && have brew; then brew install "$1"; else shift; "$@"; fi; }
inst_kubectl() { curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/$([ "$OS" = Darwin ] && echo darwin || echo linux)/$ARCH/kubectl"; sudo install -m755 /tmp/kubectl /usr/local/bin/kubectl; }
inst_kind()    { curl -fsSLo /tmp/kind "https://kind.sigs.k8s.io/dl/latest/kind-$([ "$OS" = Darwin ] && echo darwin || echo linux)-$ARCH"; sudo install -m755 /tmp/kind /usr/local/bin/kind; }
inst_helm()    { curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash; }
need() {
  have "$1" && { ok "$1"; return; }
  warn "$1 not found"
  ask "install $1?" || die "$1 is required"
  brew_or "$1" "inst_$1"
  have "$1" || die "$1 install failed — install it manually and re-run"
  ok "$1 (installed)"
}

# ============================================================================================
# uninstall
# ============================================================================================
if [ "$UNINSTALL" = 1 ]; then
  say "Removing ai-operator"
  ask "proceed?" || exit 0
  kubectl delete -k . --ignore-not-found 2>/dev/null || true
  kubectl delete -f deploy/kyverno-guardrails.yaml --ignore-not-found 2>/dev/null || true
  kubectl delete -f crds/ --ignore-not-found 2>/dev/null || true
  if [ "$PURGE" = 1 ]; then
    kubectl delete ns "$NS" --ignore-not-found
    [ "$KIND" = 1 ] && kind delete cluster --name ai-operator 2>/dev/null || true
  else
    say "namespace + PVCs (memory, models) kept. --purge also deletes those."
  fi
  exit 0
fi

# ============================================================================================
# 1. host tools
# ============================================================================================
say "Host tools"
need kubectl
[ "$KIND" = 1 ] && { need kind; have docker || die "--kind needs Docker (Docker Desktop / OrbStack / Colima)"; docker info >/dev/null 2>&1 || die "Docker daemon not reachable — start Docker and re-run"; }

# ============================================================================================
# 2. --kind ONLY: create a throwaway test cluster. Default path installs into your EXISTING cluster.
# ============================================================================================
if [ "$KIND" = 1 ]; then
  if kind get clusters 2>/dev/null | grep -qx ai-operator; then
    ok "kind cluster 'ai-operator' already exists"
  else
    say "Creating throwaway kind cluster 'ai-operator' (reuses \$HOME/.ollama models)"
    sed "s#HOST_HOME#${HOME}#" deploy/kind-cluster.yaml | kind create cluster --config -
  fi
  kubectl config use-context kind-ai-operator >/dev/null
fi

# ============================================================================================
# 3. connect to the EXISTING cluster (from this machine's kubeconfig / current context)
# ============================================================================================
say "Connecting to your cluster"
# On a control-plane node people often haven't set up a user kubeconfig — fall back to admin.conf.
if ! kubectl config current-context >/dev/null 2>&1; then
  if [ -r /etc/kubernetes/admin.conf ]; then
    export KUBECONFIG=/etc/kubernetes/admin.conf
    warn "no user kubeconfig — using /etc/kubernetes/admin.conf (you're on a control-plane node)"
  elif sudo -n test -r /etc/kubernetes/admin.conf 2>/dev/null; then
    TMPKC="$(mktemp)"; sudo cat /etc/kubernetes/admin.conf > "$TMPKC"; export KUBECONFIG="$TMPKC"
    warn "no user kubeconfig — using a copy of /etc/kubernetes/admin.conf"
  else
    die "no kubeconfig found.
    Run this from a machine that can already reach your cluster:
      * your laptop:            \`kubectl get nodes\` must work first (set up ~/.kube/config)
      * the control-plane node: \`export KUBECONFIG=/etc/kubernetes/admin.conf\` then re-run
                                (or: sudo ./install.sh)
    Or, just to try it out on a fresh local cluster:  ./install.sh --kind"
  fi
fi

CTX="$(kubectl config current-context)"
kubectl version -o json >/dev/null 2>&1 || die "context '$CTX' is set but the cluster is unreachable (VPN down? server off? wrong context?)"

SRV="$(kubectl version -o json 2>/dev/null | grep -o '\"gitVersion\": *\"[^\"]*\"' | tail -1 | cut -d'\"' -f4)"
NODES="$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')"
NOTREADY="$(kubectl get nodes --no-headers 2>/dev/null | awk '$2!="Ready"' | wc -l | tr -d ' ')"
say "Target cluster"
printf '    context : %s\n    server  : %s\n    nodes   : %s (%s not Ready)\n' "$CTX" "${SRV:-?}" "$NODES" "$NOTREADY"
case "$CTX" in *prod*|*production*) warn "this context name contains 'prod' — make sure this is intended";; esac
[ "$KIND" = 1 ] || ask "install ai-operator into THIS existing cluster?" || die "aborted"

# ---- existing-cluster preflight (fail early, not after a half-install) -----------------------
say "Preflight"
kubectl auth can-i create deployments -n default >/dev/null 2>&1 \
  && kubectl auth can-i create clusterroles >/dev/null 2>&1 \
  || die "your kubeconfig user can't create Deployments + ClusterRoles here — use an admin context"
ok "permissions"

if [ -z "$OLLAMA_EXTERNAL_URL" ]; then
  DEFSC="$(kubectl get storageclass -o jsonpath='{range .items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")]}{.metadata.name}{"\n"}{end}' 2>/dev/null)"
  if [ -z "$DEFSC" ]; then
    warn "no DEFAULT StorageClass — the memory + Ollama-models PVCs will hang as Pending."
    warn "  fix one of: mark a StorageClass default, or set OLLAMA_EXTERNAL_URL + a manual PV,"
    warn "  or install a provisioner (e.g. local-path-provisioner)."
    ask "continue anyway?" || die "aborted — no storage"
  else
    ok "default StorageClass: $DEFSC"
  fi
  # Ollama wants ~3Gi request; warn if the biggest node can't obviously fit it
  if kubectl top nodes >/dev/null 2>&1; then
    kubectl top nodes | sed 's/^/    /'
  fi
else
  ok "external Ollama configured — no in-cluster model storage needed"
fi

# ============================================================================================
# 4. CRDs + core manifests  (no build, no push)
# ============================================================================================
say "Applying CRDs"
kubectl apply -f crds/
say "Applying operator (namespace, RBAC, Ollama, config, deployment)"
kubectl apply -k .

# seed config + git secret from .env, then restart so initContainers pick up any fork/branch
kubectl -n "$NS" patch cm ai-operator-config --type merge \
  -p "{\"data\":{\"mode\":\"$MODE\",\"srcRepo\":\"$SRC_REPO\",\"srcRef\":\"$SRC_REF\"}}" >/dev/null
[ -n "$GIT_REPO_URL" ] && kubectl -n "$NS" create secret generic ai-operator-git \
  --from-literal=repoURL="$GIT_REPO_URL" --from-literal=token="$GIT_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl -n "$NS" rollout restart deploy/ai-operator >/dev/null 2>&1 || true

# ============================================================================================
# 5. Ollama
# ============================================================================================
if [ -n "$OLLAMA_EXTERNAL_URL" ]; then
  say "Using external Ollama: $OLLAMA_EXTERNAL_URL"
  kubectl -n "$NS" scale deploy/ollama --replicas=0 >/dev/null 2>&1 || true
  kubectl -n "$NS" set env deploy/ai-operator OLLAMA_HOST="$OLLAMA_EXTERNAL_URL" >/dev/null
  say "Checking reachability from inside the cluster..."
  if kubectl -n "$NS" run ollamacheck --rm -i --restart=Never --image=curlimages/curl:8.10.1 -- \
       curl -fsS -m8 "${OLLAMA_EXTERNAL_URL%/}/api/tags" >/dev/null 2>&1; then
    ok "cluster can reach $OLLAMA_EXTERNAL_URL"
  else
    warn "cluster CANNOT reach $OLLAMA_EXTERNAL_URL — the operator won't be able to think."
    warn "  fix: Ollama must bind 0.0.0.0 AND the IP must be routable from cluster pods AND"
    warn "       the host firewall must allow :11434. Then: kubectl -n $NS rollout restart deploy/ai-operator"
  fi
else
  # in-cluster Ollama. For kind, repoint its storage at the host models mount.
  if [ "$KIND" = 1 ]; then
    kubectl -n "$NS" patch deploy/ollama --type json -p '[
      {"op":"replace","path":"/spec/template/spec/volumes/0","value":{"name":"models","hostPath":{"path":"/host-ollama/models","type":"DirectoryOrCreate"}}}
    ]' >/dev/null && ok "in-cluster Ollama will reuse host models"
  fi
  say "Waiting for in-cluster Ollama..."
  kubectl -n "$NS" rollout status deploy/ollama --timeout=180s || warn "Ollama slow to start — check: kubectl -n $NS logs deploy/ollama"
  say "Pulling models the agents need (into the cluster's Ollama)"
  MODELS="$(grep -E '^[[:space:]]+model\.[A-Za-z]+:' deploy/config.yaml | awk -F'"' 'NF>=2{print $2}' | sort -u)"
  for m in $MODELS; do
    printf '    %s ' "$m"
    if kubectl -n "$NS" exec deploy/ollama -- ollama pull "$m" >/dev/null 2>&1; then echo "✓"; else echo "(will lazy-pull on first use)"; fi
  done
fi

# ============================================================================================
# 6. Kyverno backstop (optional — operator is safe without it)
# ============================================================================================
if kubectl get crd clusterpolicies.kyverno.io >/dev/null 2>&1; then
  kubectl apply -f deploy/kyverno-guardrails.yaml && ok "Kyverno guardrail policy applied"
else
  warn "Kyverno not installed. The operator is still safe (RBAC has no delete verbs + it validates"
  warn "every change and refuses data-losing edits) — Kyverno is just defence-in-depth."
  if have helm && ask "install Kyverno now (adds the enforced backstop)?"; then
    helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null 2>&1 || true
    helm repo update >/dev/null
    helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace \
      --set admissionController.replicas=1 --set backgroundController.replicas=1 \
      --set cleanupController.replicas=1 --set reportsController.replicas=1 --timeout 10m --wait \
      || warn "Kyverno pods still starting — re-run install.sh later to apply the guardrail policy"
    kubectl get crd clusterpolicies.kyverno.io >/dev/null 2>&1 && \
      kubectl apply -f deploy/kyverno-guardrails.yaml && ok "Kyverno guardrail policy applied"
  fi
fi

# ============================================================================================
# 7. wait + report
# ============================================================================================
say "Waiting for the operator (first start clones the repo + pip installs — ~2 min)"
kubectl -n "$NS" rollout status deploy/ai-operator --timeout=300s || {
  warn "not ready yet. Check:"
  echo "    kubectl -n $NS get pods"
  echo "    kubectl -n $NS logs deploy/ai-operator -c code   # git clone"
  echo "    kubectl -n $NS logs deploy/ai-operator -c deps   # pip install"
  echo "    kubectl -n $NS logs deploy/ai-operator            # the operator"
  exit 1
}

cat <<EOF

$(say "ai-operator is running.")
  mode          : ${MODE}   (observe = report only)
  watch it      : kubectl -n $NS logs deploy/ai-operator -f
  findings      : kubectl -n $NS get findings
  what it learnt: kubectl -n $NS get cm agent-memory-digest -o yaml
  go to assist  : kubectl -n $NS patch cm ai-operator-config --type merge -p '{"data":{"mode":"assist"}}'
  kill switch   : kubectl -n $NS patch cm ai-operator-config --type merge -p '{"data":{"paused":"true"}}'
EOF
