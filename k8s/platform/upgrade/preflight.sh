#!/usr/bin/env bash
# Cluster upgrade pre-flight — READ-ONLY checks + an optional etcd snapshot.
# Run this (and read every WARN/FAIL) before the kubernetes-upgrader agent touches anything.
#
#   ./preflight.sh --target 1.30 [--kubeconfig ~/.kube/config] [--context <ctx>] [--etcd-backup]
#
# Exit 0 = go, 1 = no-go (blocking findings), 2 = usage error. Nothing here mutates the cluster
# except `--etcd-backup`, which only writes a snapshot file (a backup, not a change).
set -Eeuo pipefail

TARGET="" ; CONTEXT_ARG=() ; DO_ETCD=0
BLOCKERS=0 ; WARNINGS=0
ts() { date -u +%Y%m%dT%H%M%SZ; }
info() { printf '  %s\n' "$*"; }
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
warn() { printf '  \033[33mWARN\033[0m %s\n' "$*"; WARNINGS=$((WARNINGS+1)); }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$*"; BLOCKERS=$((BLOCKERS+1)); }
hdr()  { printf '\n== %s ==\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target)     TARGET="${2:?}"; shift 2;;
    --context)    CONTEXT_ARG=(--context "${2:?}"); shift 2;;
    --kubeconfig) export KUBECONFIG="${2:?}"; shift 2;;
    --etcd-backup) DO_ETCD=1; shift;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$TARGET" ] || { echo "--target <minor, e.g. 1.30> is required" >&2; exit 2; }

kc() { kubectl "${CONTEXT_ARG[@]}" "$@"; }

hdr "Context"
CTX="$(kc config current-context)"
info "context : $CTX"
SERVER_VER="$(kc version -o json | jq -r '.serverVersion.gitVersion')"
SERVER_MINOR="$(echo "$SERVER_VER" | sed -E 's/^v?([0-9]+\.[0-9]+).*/\1/')"
info "server  : $SERVER_VER  (minor $SERVER_MINOR)"
info "target  : $TARGET"
case "$CTX" in *prod*|*production*) warn "context name contains 'prod' — treat every step as production-critical";; esac

hdr "Version path (no skipping minors)"
cur_major="${SERVER_MINOR%%.*}" ; cur_min="${SERVER_MINOR##*.}"
tgt_major="${TARGET%%.*}"        ; tgt_min="${TARGET##*.}"
if [ "$cur_major" != "$tgt_major" ] || [ "$tgt_min" -lt "$cur_min" ]; then
  fail "target $TARGET is not a forward path from $SERVER_MINOR"
else
  path="$SERVER_MINOR" ; h="$cur_min"
  while [ "$h" -lt "$tgt_min" ]; do h=$((h+1)); path="$path -> ${cur_major}.${h}"; done
  ok "path: $path  ($((tgt_min-cur_min)) hop(s))"
  [ $((tgt_min-cur_min)) -le 3 ] || warn "$((tgt_min-cur_min)) hops is a long march — consider a rebuild/blue-green instead"
fi

hdr "Node inventory & kubelet skew"
kc get nodes -o json | jq -r '
  .items[] | [.metadata.name,
    (.metadata.labels|has("node-role.kubernetes.io/control-plane") or has("node-role.kubernetes.io/master")|if . then "control-plane" else "worker" end),
    .status.nodeInfo.kubeletVersion, .status.nodeInfo.containerRuntimeVersion, .status.nodeInfo.osImage] | @tsv' \
  | column -t -s $'\t'
NOT_READY="$(kc get nodes --no-headers | awk '$2!="Ready"{print $1}' || true)"
[ -z "$NOT_READY" ] && ok "all nodes Ready" || fail "nodes not Ready: $NOT_READY"
SKEW="$(kc get nodes -o json | jq -r '[.items[].status.nodeInfo.kubeletVersion | sub("^v";"") | split(".")[1]|tonumber] | (max-min)')"
[ "${SKEW:-0}" -le 2 ] && ok "kubelet minor skew = ${SKEW:-0} (<=2)" || fail "kubelet minor skew = $SKEW — upgrade lagging nodes first"

hdr "Control-plane / cluster health"
if kc get --raw='/readyz?verbose' >/tmp/readyz 2>/dev/null; then
  grep -q '^readyz check passed' /tmp/readyz && ok "/readyz passed" || { warn "/readyz not fully passing:"; grep -v ' ok$' /tmp/readyz | sed 's/^/    /'; }
else
  warn "could not query /readyz (RBAC?) — check control-plane health manually"
fi
BADAPI="$(kc get apiservices -o json | jq -r '.items[] | select(.status.conditions[]?|select(.type=="Available" and .status!="True")) | .metadata.name' || true)"
[ -z "$BADAPI" ] && ok "all APIServices Available" || fail "APIServices not Available (fix before upgrade): $BADAPI"
CLB="$(kc get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers 2>/dev/null | wc -l | tr -d ' ')"
[ "$CLB" = "0" ] && ok "no not-Running pods" || warn "$CLB pod(s) not Running/Succeeded — investigate before adding disruption"
if kc get clusteroperators >/dev/null 2>&1; then
  BADCO="$(kc get clusteroperators -o json | jq -r '.items[] | select(.status.conditions[]|select((.type=="Available" and .status!="True") or (.type=="Degraded" and .status=="True"))) | .metadata.name' || true)"
  [ -z "$BADCO" ] && ok "OpenShift clusteroperators all Available, none Degraded" || fail "clusteroperators unhealthy: $BADCO"
fi

hdr "Deprecated / removed API scan"
FOUND_SCANNER=0
if command -v kubent >/dev/null 2>&1; then
  FOUND_SCANNER=1
  info "running kubent --target-version ${TARGET} ..."
  if kubent --target-version "v${TARGET}.0" -e 2>/dev/null; then ok "kubent: nothing removed at v${TARGET}"; else fail "kubent found APIs removed by v${TARGET} — fix manifests in Git first"; fi
fi
if command -v pluto >/dev/null 2>&1; then
  FOUND_SCANNER=1
  info "running pluto detect-all-in-cluster --target-versions k8s=v${TARGET}.0 ..."
  if pluto detect-all-in-cluster --target-versions "k8s=v${TARGET}.0" --only-show-removed 2>/dev/null | grep -q .; then
    fail "pluto found removed APIs at v${TARGET} — fix in Git first"; pluto detect-all-in-cluster --target-versions "k8s=v${TARGET}.0" --only-show-removed | sed 's/^/    /'
  else ok "pluto: no removed APIs at v${TARGET}"; fi
fi
[ "$FOUND_SCANNER" = "1" ] || warn "neither kubent nor pluto installed — install one and re-run; this is the #1 cause of workloads vanishing mid-upgrade"

hdr "PodDisruptionBudgets that could block node drain"
PDB_BAD=0
while IFS=$'\t' read -r ns name allowed healthy; do
  [ -n "$ns" ] || continue
  if [ "$allowed" -eq 0 ] 2>/dev/null; then
    fail "PDB $ns/$name disruptionsAllowed=0 (healthy=$healthy) — drain hangs forever; relax it or scale the workload up first"
    PDB_BAD=$((PDB_BAD+1))
  fi
done < <(kc get pdb -A -o json | jq -r '
  .items[] | select((.status.expectedPods // 0) > 0) |
  [.metadata.namespace, .metadata.name, (.status.disruptionsAllowed // 0), "\(.status.currentHealthy // 0)/\(.status.expectedPods)"] | @tsv')
[ "$PDB_BAD" -eq 0 ] && ok "no drain-blocking PDBs (re-check after any scale-down during the upgrade)"

hdr "Single points of failure (replicas < 2 — brief downtime when that node drains)"
SPOF="$(kc get deploy,statefulset -A -o json | jq -r '
  [.items[] | select((.spec.replicas // 1) < 2) | .metadata.namespace] | group_by(.) |
  map("\(.[0])(\(length))") | join(" ")')"
if [ -n "$SPOF" ] && [ "$SPOF" != "" ]; then
  warn "single-replica workloads by namespace: $SPOF"
  info "acceptable for controllers/operators; scale user-facing services to >=2 with anti-affinity before a prod upgrade"
else
  ok "every Deployment/StatefulSet has >=2 replicas"
fi

hdr "Add-ons to check for target-minor support (verify versions manually against their docs)"
for n in kube-system; do
  kc -n "$n" get deploy,daemonset -o json | jq -r '.items[] |
    [.kind, .metadata.name,
     (.spec.template.spec.containers[0].image | split(":")[1] // "?")] | @tsv' | column -t -s $'\t' | sed 's/^/  /'
done
info "also check: CNI (calico/cilium/vpc-cni), CSI drivers, ingress controller, cert-manager,"
info "prometheus-operator, service mesh — each needs a release that supports v${TARGET}."

hdr "Node capacity headroom for surge (one node out)"
kc top nodes 2>/dev/null | sed 's/^/  /' || warn "metrics-server not available — can't check live utilization"

if [ "$DO_ETCD" = "1" ]; then
  hdr "etcd snapshot (kubeadm static-pod etcd)"
  SNAP="/var/lib/etcd-backup/preflight-$(ts).db"
  info "attempting: sudo ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \\"
  info "  --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt \\"
  info "  --key /etc/kubernetes/pki/etcd/server.key snapshot save $SNAP"
  if sudo -n true 2>/dev/null && [ -f /etc/kubernetes/pki/etcd/server.crt ]; then
    sudo mkdir -p /var/lib/etcd-backup
    sudo ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
      --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt \
      --key /etc/kubernetes/pki/etcd/server.key snapshot save "$SNAP"
    sudo ETCDCTL_API=3 etcdctl --write-out=table snapshot status "$SNAP" | sed 's/^/  /'
    warn "COPY $SNAP OFF THIS NODE before upgrading. Restore: etcdctl snapshot restore $SNAP"
  else
    warn "run this on a control-plane node with sudo; managed control planes (EKS/AKS/GKE/OpenShift) back themselves up"
  fi
fi

hdr "Verdict"
printf '  blockers: %s   warnings: %s\n' "$BLOCKERS" "$WARNINGS"
if [ "$BLOCKERS" -gt 0 ]; then
  printf '  \033[31mNO-GO\033[0m — resolve the FAIL items, then re-run.\n'
  exit 1
fi
printf '  \033[32mGO\033[0m — review WARNs with the user, then proceed hop-by-hop (see kubernetes-upgrader agent).\n'
