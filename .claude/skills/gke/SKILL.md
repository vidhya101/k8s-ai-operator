---
name: gke
description: Google GKE-specific concerns — Workload Identity Federation, Autopilot vs. Standard, VPC-native networking, and GKE Ingress/Gateway. Use alongside the kubernetes skill when the target cluster is GKE.
---

# GKE (Google Kubernetes Engine)

GKE-specific delta on top of the `kubernetes` core skill.

## Identity: Workload Identity Federation

- Pods authenticate as a Google Cloud service account via a Kubernetes ServiceAccount binding — no
  downloaded service-account-key JSON files in the pod.
- Check: the Kubernetes ServiceAccount has the `iam.gke.io/gcp-service-account` annotation, and the GCP
  service account's IAM policy grants `roles/iam.workloadIdentityUser` scoped to the specific
  `<project>.svc.id.goog[<namespace>/<ksa-name>]` member, not broadly.

## Autopilot vs. Standard

- **Autopilot**: Google manages nodes entirely (no node pool management, no node-level `kubectl`/SSH
  access); pod-level resource requests directly drive billing; some workload types are restricted
  (privileged containers, hostPath, DaemonSets are limited/disallowed). Good default when the team wants
  less operational surface and doesn't need node-level control.
- **Standard**: full node pool control (machine types, node count, taints), supports the full range of
  workload types including privileged/DaemonSet-heavy setups — needed for GPU scheduling nuances, custom
  node configuration, or node-level agents. Standard requires managing node upgrades/scaling explicitly
  (or via Cluster Autoscaler).
- Don't assume which mode a cluster is in — `gcloud container clusters describe` states it explicitly.

## Networking

- VPC-native (alias IP ranges) is the default and recommended mode — pods get IPs from a secondary range
  in the VPC subnet; size the secondary range for expected pod count, same IP-planning discipline as
  EKS/AKS.
- GKE Ingress (via GCE load balancer) or Gateway API — check which the cluster/manifests actually use;
  don't assume Ingress annotations from another cloud's controller apply here.

## Key Commands

```bash
gcloud container clusters get-credentials <cluster> --zone/--region <location>
gcloud container clusters describe <cluster> --format="value(autopilot.enabled)"
gcloud container node-pools list --cluster <cluster>
kubectl get sa <name> -n <ns> -o yaml   # check the workload identity annotation
```

## Common Pitfalls

- Workload Identity Federation IAM binding granted at the project level instead of scoped to the specific
  KSA member string — over-broad access any workload identity-enabled pod could potentially use.
- Assuming Standard-cluster capabilities (privileged pods, hostPath, arbitrary DaemonSets) on an Autopilot
  cluster — the pod will be rejected or need a different approach.
- VPC-native secondary range sized too small for planned pod scale, requiring a new subnet/range and
  migration rather than a simple resize.
