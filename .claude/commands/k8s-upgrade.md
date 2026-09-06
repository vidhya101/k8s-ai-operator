---
description: Plan and (with confirmation at every phase) execute a full cluster upgrade — control plane + worker nodes — one minor at a time.
argument-hint: "<target version, e.g. '1.30'> [--plan-only] [context or cluster name]"
---

Upgrade this Kubernetes cluster: $ARGUMENTS

Delegate to the `kubernetes-upgrader` agent, loading the `kubernetes` skill plus the distro skill
(`kubeadm` / `eks` / `aks` / `gke` / `openshift`) once the cluster is fingerprinted, and
`velero` / `external-secrets` if stateful backups are in scope.

1. Confirm `kubectl config current-context`, distro, environment, and prod status. Refuse to run
   against an ambiguous target (`.claude/rules/environment-awareness.md`).
2. Build the stepped version path — **never skip a minor** (1.28→1.30 is two cycles).
3. Run the full pre-flight for the whole path: release-note review, `kubent`/`pluto` deprecated-API
   scan (fix in Git first), add-on compatibility, **etcd snapshot** (kubeadm/k3s-HA), health
   baseline, PDB/drain readiness (flag any `maxUnavailable:0` PDB that would block drain forever),
   surge capacity, cert state, PV backups. Present a **go / no-go**.
4. `--plan-only` → stop here with the CONTEXT/CURRENT/PATH/PRE-FLIGHT/RISKS/ROLLBACK block.
5. Otherwise execute per hop, per phase — **A** control plane (first CP node `kubeadm upgrade
   apply`, others `kubeadm upgrade node`, then kubelet; managed: control-plane-only upgrade) →
   **B** add-ons that must track the CP (CNI/CSI/CoreDNS/kube-proxy) → **C** workers one at a time
   (cordon → drain → upgrade → uncordon → verify; a drain blocked by a PDB is a STOP, never
   `--force`) → **D** post-hop verification.
6. **Stop for explicit confirmation at every phase boundary.** Every mutating command
   (`kubeadm upgrade`, `az aks upgrade`, `oc adm upgrade`, `drain`, node package upgrades) is shown
   before it runs — no `-y`/`--yes`/`-auto-approve` to bypass the gate (`.claude/rules/safety.md`).
7. State the distro-specific rollback path before step 5, and stop + surface it on any failed
   verification.

End with: the path executed, per-node/per-pool result, verification status, and anything left for
the user (a workload still on an old API, a PDB that had to be relaxed, a node pool not yet retired).
