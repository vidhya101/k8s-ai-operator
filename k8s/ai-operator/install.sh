#!/usr/bin/env bash
# ai-operator installer — deploys into your EXISTING Kubernetes cluster.
# No image build, no registry, no host networking.
#
#   ./install.sh                 # lists your kube contexts, asks which cluster, installs there
#   ./install.sh --context NAME  # skip the prompt, use that context (or KUBE_CONTEXT in .env)
#                                #   - laptop:  `kubectl get nodes` must already work
#                                #   - control-plane node:  run as-is (uses admin.conf) or `sudo ./install.sh`
#   ./install.sh --kind          # NO cluster yet? spin up a throwaway local one to try it
#   ./install.sh --yes           # no prompts (CI; uses current context unless --context given)
#   ./install.sh --uninstall     # remove the operator (keeps memory/models PVCs unless --purge)
#
#   cp env.template .env         # OPTIONAL — every setting has a working default
#
# Host needs: kubectl. (helm only if you opt into Kyverno; kind + docker only for --kind.)
set -Eeuo pipefail
cd "$(dirname "$0")"

# ---- args ---------------------------------------------------------------------------------------
YES=0 KIND=0 UNINSTALL=0 PURGE=0 CTX_FLAG=""
while [ $# -gt 0 ]; do case "$1" in
  -y|--yes) YES=1;; --kind) KIND=1;; --uninstall) UNINSTALL=1;; --purge) PURGE=1;;
  --context) CTX_FLAG="${2:?--context needs a value}"; shift;;
  --context=*) CTX_FLAG="${1#*=}";;
  -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  *) echo "unknown arg: $1" >&2; exit 2;;
esac; shift; done

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
ask()  { [ "$YES" = 1 ] && return 0; printf '    %s [y/N] ' "$1"; read -r r; [ "$r" = y ] || [ "$r" = Y ]; }
have() { command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"; ARCH="$(uname -m)"; case "$ARCH" in x86_64) ARCH=amd64;; arm64|aarch64) ARCH=arm64;; esac
NS=ai-operator

# ---- .env (read per-key — never sourced; portable to bash 3.2 / POSIX) -----------------------
env_get() {
  local key="$1" def="${2:-}" val=""
  if [ -f .env ]; then
    val="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" .env 2>/dev/null | head -1 \
      | sed 's/^[^=]*=//; s/[[:space:]]*#.*$//; s/^[[:space:]]*//; s/[[:space:]]*$//; s/^"//; s/"$//; s/^'"'"'//; s/'"'"'$//')"
  fi
  [ -n "$val" ] && printf '%s' "$val" || printf '%s' "$def"
}
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
# 3. pick the cluster (existing kubeconfig contexts) + snapshot its health
# ============================================================================================
KC="$(env_get KUBE_CONTEXT)"; [ -n "$CTX_FLAG" ] && KC="$CTX_FLAG"

if [ "$KIND" = 1 ]; then
  kubectl config use-context kind-ai-operator >/dev/null

elif ! kubectl config current-context >/dev/null 2>&1 && [ -z "$KC" ]; then
  # No kubeconfig at all — try the control-plane node's admin.conf, else explain.
  if [ -r "$HOME/.kube/config" ]; then :; fi
  if sudo -n test -r /etc/kubernetes/admin.conf 2>/dev/null || [ -r /etc/kubernetes/admin.conf ]; then
    TMPKC="$(mktemp)"; { cat /etc/kubernetes/admin.conf 2>/dev/null || sudo cat /etc/kubernetes/admin.conf; } > "$TMPKC"
    export KUBECONFIG="$TMPKC"
    warn "no user kubeconfig — using /etc/kubernetes/admin.conf (control-plane node)"
  else
    die "No kubeconfig found. Run this where you can already reach a cluster:
      * laptop:            get \`kubectl get nodes\` working first (set KUBECONFIG or ~/.kube/config)
      * control-plane node: re-run as \`sudo ./install.sh\`
      * no cluster yet:     ./install.sh --kind"
  fi

else
  # Enumerate contexts and let the user choose.
  CTX_NAMES="$(kubectl config get-contexts -o name 2>/dev/null || true)"
  CUR="$(kubectl config current-context 2>/dev/null || true)"
  N=0; while IFS= read -r c; do [ -n "$c" ] && N=$((N+1)); done <<EOF
$CTX_NAMES
EOF

  if [ -n "$KC" ]; then
    printf '%s\n' "$CTX_NAMES" | grep -qx "$KC" || die "context '$KC' not in kubeconfig. Available:
$(printf '%s\n' "$CTX_NAMES" | sed 's/^/      /')"
    kubectl config use-context "$KC" >/dev/null
  elif [ "$N" -le 1 ]; then
    :   # single context — just use it
  elif [ "$YES" = 1 ]; then
    warn "multiple contexts; using current ($CUR). Pass --context <name> or KUBE_CONTEXT to choose."
  else
    say "Which cluster? (kube contexts in your kubeconfig)"
    i=0
    while IFS= read -r c; do
      [ -n "$c" ] || continue
      i=$((i+1)); eval "CTX_$i=\$c"
      cl="$(kubectl config view -o "jsonpath={.contexts[?(@.name=='$c')].context.cluster}" 2>/dev/null)"
      sv="$(kubectl config view -o "jsonpath={.clusters[?(@.name=='$cl')].cluster.server}" 2>/dev/null)"
      mk=' '; [ "$c" = "$CUR" ] && mk='*'
      printf '    %s %2d) %-40s %s\n' "$mk" "$i" "$c" "$sv"
    done <<EOF
$CTX_NAMES
EOF
    printf '    choose [1-%d, Enter = current "%s"]: ' "$i" "$CUR"
    read -r pick
    if [ -n "$pick" ]; then
      case "$pick" in *[!0-9]*|'') die "not a number";; esac
      [ "$pick" -ge 1 ] && [ "$pick" -le "$i" ] || die "out of range"
      eval "CHOSEN=\$CTX_$pick"
      kubectl config use-context "$CHOSEN" >/dev/null
    fi
  fi
fi

CTX="$(kubectl config current-context 2>/dev/null || echo '?')"
kubectl version -o json >/dev/null 2>&1 || die "context '$CTX' is set but the cluster is unreachable (VPN? server down? wrong context?)"

# ---- health snapshot — informative, NOT a gate. A cluster in bad shape is the whole point. ---
SRV="$(kubectl version -o json 2>/dev/null | grep -o '"gitVersion": *"[^"]*"' | tail -1 | cut -d'"' -f4)"
say "Target: $CTX   (server ${SRV:-?})"
NT="$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')"
NR="$(kubectl get nodes --no-headers 2>/dev/null | awk '$2=="Ready"' | wc -l | tr -d ' ')"
[ "$NR" = "$NT" ] && [ "$NT" != 0 ] && ok "nodes: $NR/$NT Ready" || warn "nodes: $NR/$NT Ready"
kubectl get --raw='/readyz' >/dev/null 2>&1 && ok "API server: healthy" \
  || warn "API server /readyz failing — installing anyway (this operator is meant to help fix that)"

# The scheduler + controller-manager MUST be up or nothing new will ever be placed — check explicitly.
SCHED="$(kubectl -n kube-system get pods -l component=kube-scheduler --no-headers 2>/dev/null | awk '{print $3}' | sort -u | tr '\n' ',' )"
CM="$(kubectl -n kube-system get pods -l component=kube-controller-manager --no-headers 2>/dev/null | awk '{print $3}' | sort -u | tr '\n' ',')"
if printf '%s' "$SCHED" | grep -qv 'Running' && [ -n "$SCHED" ]; then
  warn "kube-scheduler is $SCHED — NOTHING will schedule until it's fixed."
  warn "  usual cause on a small/loaded cluster: apiserver/etcd too slow -> scheduler loses its"
  warn "  leader lease and crashloops. On the control-plane node:"
  warn "    sudo crictl ps -a | grep -E 'etcd|apiserver|scheduler'"
  warn "    sudo crictl logs \$(sudo crictl ps -a --name kube-scheduler -q | head -1) 2>&1 | tail -30"
  warn "    free -h ; df -h /var/lib/etcd    # OOM? disk full/slow?"
  warn "  band-aid: add to /etc/kubernetes/manifests/kube-scheduler.yaml (and kube-controller-manager.yaml):"
  warn "    --leader-elect-lease-duration=30s --leader-elect-renew-deadline=20s --leader-elect-retry-period=4s"
  ask "the operator install WILL hang until this is fixed. Continue anyway?" || die "fix the scheduler first"
elif [ -n "$SCHED" ]; then ok "kube-scheduler: Running"; fi
[ -n "$CM" ] && printf '%s' "$CM" | grep -qv 'Running' && warn "kube-controller-manager is $CM (same root cause as a bad scheduler)" || true

BADP="$(kubectl get pods -A --no-headers 2>/dev/null | awk '$4!="Running"&&$4!="Completed"&&$4!="Succeeded"' | wc -l | tr -d ' ')"
[ "$BADP" = 0 ] && ok "no failing pods cluster-wide" \
  || warn "$BADP pod(s) not Running cluster-wide — the operator will open findings for these"
case "$CTX" in *prod*|*production*) warn "context name contains 'prod' — confirm this is intended";; esac
[ "$KIND" = 1 ] || ask "install ai-operator into '$CTX'?" || die "aborted"

# ---- hard gates (these genuinely block a working install) -----------------------------------
say "Preflight"
kubectl auth can-i create deployments -A >/dev/null 2>&1 \
  && kubectl auth can-i create clusterroles >/dev/null 2>&1 \
  || die "this kubeconfig user can't create Deployments + ClusterRoles — use an admin context (--context)"
ok "permissions"

if [ -z "$OLLAMA_EXTERNAL_URL" ]; then
  DEFSC="$(kubectl get sc -o jsonpath='{range .items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")]}{.metadata.name}{"\n"}{end}' 2>/dev/null | head -1)"
  if [ -z "$DEFSC" ]; then
    warn "no DEFAULT StorageClass — the operator's PVCs (memory + models) would hang Pending."
    warn "  options: (a) mark a StorageClass default:"
    warn "             kubectl annotate sc <name> storageclass.kubernetes.io/is-default-class=true"
    warn "           (b) set OLLAMA_EXTERNAL_URL in .env (skips the models PVC; memory still needs a bit)"
    warn "           (c) install a provisioner: helm/kubectl for local-path-provisioner"
    ask "continue anyway?" || die "aborted — sort out storage first"
  else
    ok "default StorageClass: $DEFSC"
  fi
else
  ok "external Ollama — no in-cluster model storage needed"
fi

# ============================================================================================
# 4. CRDs + core manifests  (server-side apply -> idempotent re-runs; failures reported, not fatal)
# ============================================================================================
apply() {  # $@ = kubectl apply args; on failure show what broke and ask
  if kubectl apply --server-side --force-conflicts "$@" 2>/tmp/aiop-apply.err; then return 0; fi
  warn "some resources did not apply:"
  sed 's/^/      /' /tmp/aiop-apply.err
  ask "continue with the rest?" || die "aborted"
}
say "Applying CRDs"
apply -f crds/
kubectl wait --for=condition=established --timeout=60s \
  crd/findings.ai-operator.io crd/remediations.ai-operator.io >/dev/null 2>&1 || \
  warn "CRDs not established yet — the operator will retry its watches"
say "Applying operator (namespace, RBAC, Ollama, config, deployment)"
apply -k .

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
  say "Checking reachability from a pod in the cluster..."
  kubectl -n "$NS" delete pod ollamacheck --ignore-not-found >/dev/null 2>&1 || true
  cat <<YAML | kubectl apply -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata: { name: ollamacheck, namespace: $NS, labels: { app.kubernetes.io/name: ai-operator } }
spec:
  restartPolicy: Never
  securityContext: { runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: c
      image: curlimages/curl:8.10.1
      args: ["--fail","--silent","--show-error","--max-time","8","${OLLAMA_EXTERNAL_URL%/}/api/tags"]
      securityContext: { allowPrivilegeEscalation: false, capabilities: { drop: ["ALL"] } }
YAML
  kubectl -n "$NS" wait --for=condition=Ready pod/ollamacheck --timeout=25s >/dev/null 2>&1 || true
  sleep 4
  OLLA_PHASE="$(kubectl -n "$NS" get pod ollamacheck -o jsonpath='{.status.phase}' 2>/dev/null || echo Unknown)"
  kubectl -n "$NS" delete pod ollamacheck --ignore-not-found >/dev/null 2>&1 || true
  if [ "$OLLA_PHASE" = Succeeded ]; then
    ok "cluster can reach $OLLAMA_EXTERNAL_URL"
  else
    warn "cluster could NOT reach $OLLAMA_EXTERNAL_URL (check pod phase: $OLLA_PHASE)."
    warn "  the operator will keep retrying. Fix on the Ollama host, then:"
    warn "    1) bind it wide:  OLLAMA_HOST=0.0.0.0:11434 ollama serve   (macOS: launchctl setenv OLLAMA_HOST 0.0.0.0:11434 then restart Ollama)"
    warn "    2) allow :11434 through the host firewall"
    warn "    3) confirm cluster nodes can route to that IP"
    warn "    then: kubectl -n $NS rollout restart deploy/ai-operator"
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
say "Waiting for the operator (first start pulls 3 images + clones repo + pip installs — 3-6 min)"
if ! kubectl -n "$NS" rollout status deploy/ai-operator --timeout=420s; then
  POD="$(kubectl -n "$NS" get pod -l app.kubernetes.io/name=ai-operator -o name 2>/dev/null | head -1)"
  warn "operator not ready yet. Current state:"
  kubectl -n "$NS" get pods -l app.kubernetes.io/name=ai-operator 2>/dev/null | sed 's/^/    /'
  if [ -n "$POD" ]; then
    echo "    --- events ---"
    kubectl -n "$NS" describe "$POD" 2>/dev/null | sed -n '/Events:/,$p' | sed 's/^/    /'
  fi
  cat <<TIP

  It usually just needs more time (slow image pull / pip). Keep watching:
    kubectl -n $NS get pods -w
    kubectl -n $NS logs deploy/ai-operator -c tools -f    # kubectl+helm download
    kubectl -n $NS logs deploy/ai-operator -c code  -f    # git clone
    kubectl -n $NS logs deploy/ai-operator -c deps  -f    # pip install
    kubectl -n $NS logs deploy/ai-operator          -f    # the operator itself
  If a pod is Pending on resources, this cluster is short on capacity — free some, or use --kind.
TIP
  exit 1
fi

cat <<EOF

$(say "ai-operator is running.")
  mode          : ${MODE}   (observe = report only)
  watch it      : kubectl -n $NS logs deploy/ai-operator -f
  findings      : kubectl -n $NS get findings
  what it learnt: kubectl -n $NS get cm agent-memory-digest -o yaml
  go to assist  : kubectl -n $NS patch cm ai-operator-config --type merge -p '{"data":{"mode":"assist"}}'
  kill switch   : kubectl -n $NS patch cm ai-operator-config --type merge -p '{"data":{"paused":"true"}}'
EOF
