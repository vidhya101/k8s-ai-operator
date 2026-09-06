---
name: velero
description: Velero — Kubernetes cluster-level backup and restore (resources + persistent volume data), including cross-cluster/cross-region migration. Use for cluster-wide backup/DR planning, distinct from kubeadm's etcd-only backup or a single application's database backup.
---

# Velero

Backs up Kubernetes resources (manifests) and, via plugins, the underlying persistent volume data —
distinct from `kubeadm`'s etcd snapshot (which captures cluster *state* but not a portable,
per-namespace/per-application backup) and from `database-operations`' application-level backup discipline
(which Velero doesn't replace for anything needing point-in-time transactional consistency).

## What Velero Backs Up

- **Kubernetes API objects**: Deployments, Services, ConfigMaps, Secrets, PVCs, etc. — serialized and
  stored in object storage (S3, GCS, Azure Blob).
- **Persistent volume data**: via CSI snapshots (preferred, if the storage driver supports it) or
  Velero's File System Backup (restic/kopia-based, works across most volume types but is slower and
  more resource-intensive) — know which mode a given backup schedule actually uses.

## Common Uses

```bash
velero backup create my-backup --include-namespaces my-ns
velero backup create nightly --schedule="0 2 * * *" --include-namespaces my-ns   # recurring
velero restore create --from-backup my-backup
velero backup describe my-backup --details
```

- **Disaster recovery**: restore an entire namespace/cluster's state after a catastrophic failure —
  the cluster-level analog to the `database-operations` skill's "verify backups are actually restorable"
  principle; a Velero backup that's never been restore-tested carries the same false confidence risk.
- **Cluster migration**: back up from one cluster (or cloud/region), restore into another — a practical
  mechanism for the kind of multi-region/DR architecture the `architecture-review` skill discusses,
  rather than a purely theoretical capability.
- **Namespace-level "undo"**: back up before a risky change (a large migration, a major upgrade) as a
  fast rollback path distinct from `kubectl rollout undo` (which only reverts a Deployment's pod spec,
  not the full set of resources/data in a namespace).

## Common Pitfalls

- Backups that only capture API objects with no PV data plugin configured — a "successful" backup that
  silently excludes the actual application data, discovered only when a restore doesn't bring the data back.
- No restore ever tested — identical to the `database-operations` skill's core warning, just at the
  cluster-resource level instead of the database level.
- Backup storage location credentials/bucket scoped too broadly, or the backup bucket itself not
  protected against deletion — a backup store that's as vulnerable as the primary cluster defeats the
  purpose of having it as a separate recovery path.
- Restoring into a cluster with a different storage class/CSI driver than the backup source, without
  checking PV restore compatibility first — cross-cluster restore of volume data specifically needs the
  target to support the same (or a mapped) storage class.
