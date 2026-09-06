---
name: kubeadm
description: Self-managed Kubernetes with kubeadm — HA control plane, etcd backup/restore, CNI selection, and version upgrades. Use alongside the kubernetes skill when the cluster is self-managed rather than a managed cloud offering.
---

# kubeadm (Self-Managed Kubernetes)

Unlike EKS/AKS/GKE, kubeadm clusters put control-plane HA, etcd health, CNI choice, and upgrade
sequencing entirely on the operator. Ansible (see `ansible` skill) typically handles node bootstrapping;
this skill covers the cluster-level concerns.

## Control Plane HA

- Odd number of etcd members (3 or 5) for quorum tolerance — an even number doesn't improve fault
  tolerance and risks split-brain.
- Stacked etcd (etcd co-located on control-plane nodes) is simpler to operate; external etcd cluster
  decouples etcd's lifecycle from the control plane's — pick based on the team's operational capacity, not
  by default.
- Load balancer (or kube-vip / keepalived VIP) in front of the API servers for HA — `kubeadm init` needs
  `--control-plane-endpoint` pointed at this VIP/LB from the start; retrofitting it onto a single-node
  control plane later is disruptive.

## etcd Backup & Restore

```bash
# Backup
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-snapshot.db
```

Schedule this on a cadence matching the cluster's RPO (see `.claude/rules` and the `sre`/`architecture-review`
skills for defining RPO) and test the restore procedure — an untested etcd backup is not a backup.

## CNI

- Calico or Cilium are the common choices; the CNI must be installed before any pod other than
  control-plane/system pods can schedule — nodes stay `NotReady` until it's applied.
- NetworkPolicy enforcement depends on CNI choice — confirm the installed CNI actually enforces
  NetworkPolicy (both do; some minimal/legacy CNIs don't) before relying on it for segmentation.

## Upgrades

```bash
kubeadm upgrade plan                        # on a control-plane node, see what's available
kubeadm upgrade apply v1.xx.x                # first control-plane node
kubeadm upgrade node                         # subsequent control-plane / worker nodes
kubectl drain <node> --ignore-daemonsets     # before upgrading kubelet on a node
apt-get install -y kubelet=1.xx.x-*          # or distro equivalent, matching the planned version
kubectl uncordon <node>
```

Upgrade one minor version at a time (kubeadm does not support skipping minor versions), control plane
before workers, and never more than one control-plane node down at once for etcd quorum.

## Common Pitfalls

- Kubelet certificate expiry (default 1 year, auto-rotated only if `--rotate-certificates` and the
  approver are configured) silently taking a node `NotReady` — check `kubeadm certs check-expiration`.
- Single-node control plane with no VIP, making HA impossible to add without a disruptive rebuild.
- CNI and kube-proxy mode (iptables vs. IPVS) mismatched expectations causing subtle Service routing
  issues that don't show up until scale.
