# `upgrade/` — full cluster version upgrades (control plane + workers)

Driven by the **`kubernetes-upgrader`** agent (`/k8s-upgrade`). This directory holds the
read-only pre-flight; the agent holds the per-distro execution runbook.

## Rules that never bend

1. **One minor at a time.** 1.28 → 1.31 is three cycles. kubeadm and every managed control plane
   enforce it; the kubelet skew policy (nodes may trail the API server by ≤ 2 minors, never lead)
   forbids the jump anyway.
2. **Control plane first, then workers.** Within the control plane: the first node runs
   `kubeadm upgrade apply`; the rest run `kubeadm upgrade node`. Never a worker before the API
   server is on the new minor.
3. **Add-ons that talk to the API move with the control plane** — CoreDNS, kube-proxy, the CNI,
   CSI drivers, metrics-server. Bump them in the gap between Phase A and Phase C.
4. **A drain blocked by a PodDisruptionBudget is a STOP, not a `--force`.** Relax the PDB or scale
   the workload up, then continue.
5. **etcd snapshot before touching a self-managed control plane.** Copied off-cluster. Managed
   control planes (EKS/AKS/GKE/OpenShift) back themselves up and **cannot be rolled back to a lower
   minor** — for those the safety net is the pre-flight + workload/PV backups + a maintenance window.
6. **Every mutating command is shown and confirmed.** No `-y` / `--yes` / `-auto-approve`.

## Run the pre-flight

```bash
# read-only; add --etcd-backup only when run ON a kubeadm control-plane node with sudo
./preflight.sh --target 1.30 [--context <ctx>] [--kubeconfig <path>] [--etcd-backup]
```

Checks: forward version path + hop count · node inventory + kubelet skew · `/readyz` + APIServices
+ (OpenShift) clusteroperators · **deprecated/removed API scan** (`kubent` and/or `pluto` — install
at least one) · **drain-blocking PDBs** (`disruptionsAllowed=0`) · single-replica workloads ·
core add-on image versions to verify · live node utilization for surge headroom · optional etcd
snapshot. Exit 0 = go, 1 = no-go.

Install the scanners first:
```bash
# kubent
sh -c "$(curl -sSL https://git.io/install-kubent)"
# pluto
brew install FairwindsOps/tap/pluto      # or grab the release binary
```

## Execution phases (the agent walks these, pausing at each boundary)

```
per minor-version hop:
  A. Control plane   first CP node upgrade apply → other CP nodes upgrade node → kubelet, all CP
                     (managed: control-plane-only upgrade)   ── verify: server on new minor, API healthy
  B. Add-ons         CNI · CSI · CoreDNS · kube-proxy · metrics-server to a target-supporting version
  C. Workers         one node (or surge batch) at a time: cordon → drain → upgrade → uncordon → verify
  D. Post-hop        all nodes Ready on new version · kubent clean for NEXT hop · canary smoke test
```

## Rollback quick reference

| Distro | If the control plane breaks | If a worker won't rejoin |
|---|---|---|
| kubeadm / k3s-HA / RKE2 | `etcdctl snapshot restore` from the pre-flight snapshot, repoint the static-pod manifest, restart — **explicit user go-ahead required** | `kubectl delete node` + re-`join` at the new version, or rebuild from image |
| EKS / AKS / GKE | forward-only — fix fast; restore workloads/PVs from backup; keep the old node pool until the new is proven | cordon new pool / uncordon old pool to shift workloads back |
| OpenShift | forward-only once the MCO has progressed; `oc adm upgrade --to-image` to a prior patch only within the same minor and only if MCO hasn't finished | MCO handles node rebuilds; check `oc get mcp` |
