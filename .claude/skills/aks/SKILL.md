---
name: aks
description: Azure AKS-specific concerns — Workload Identity, Azure CNI vs. kubenet, cluster autoscaler, and AGIC/Application Gateway ingress. Use alongside the kubernetes skill when the target cluster is AKS.
---

# AKS (Azure Kubernetes Service)

AKS-specific delta on top of the `kubernetes` core skill.

## Identity: Workload Identity

- Azure AD Workload Identity (successor to the older AAD Pod Identity) — pods federate to an Azure AD
  app/managed identity via a ServiceAccount annotation, no static Azure credentials in the pod.
- Check: ServiceAccount has `azure.workload.identity/client-id` annotation and the pod template has
  `azure.workload.identity/use: "true"`; the federated credential on the Azure AD app is scoped to the
  specific namespace + ServiceAccount subject.

## Networking

- Azure CNI (pods get real VNet IPs) vs. kubenet (pods get an overlay IP, NATed) — this decision is made
  at cluster creation and affects subnet sizing: Azure CNI needs a subnet sized for pod count, not just
  node count, same IP-exhaustion risk profile as EKS's VPC CNI.
- Azure CNI Overlay (newer option) decouples pod IPs from the VNet address space while keeping most of
  Azure CNI's functionality — check which variant a given cluster actually uses before sizing anything.
- AGIC (Application Gateway Ingress Controller) manages an Application Gateway from Ingress resources;
  alternatively, plain `LoadBalancer` Services provision an Azure Load Balancer directly.

## Compute

- Cluster Autoscaler (node pool min/max count) is the standard scaling mechanism; node pools can be
  system (control-plane-adjacent workloads) or user pools (application workloads) — keep application
  workloads off the system pool where possible.
- Spot node pools available for interruption-tolerant workloads at lower cost — never place stateful or
  availability-critical workloads on a spot-only pool without a fallback.

## Key Commands

```bash
az aks get-credentials --resource-group <rg> --name <cluster>
az aks show --resource-group <rg> --name <cluster> --query networkProfile
az aks nodepool list --resource-group <rg> --cluster-name <cluster>
kubectl get pods -n kube-system -l component=cluster-autoscaler
```

## Common Pitfalls

- Workload Identity federated credential subject mismatched to the actual namespace/ServiceAccount name
  (a copy-paste from another environment) — the pod silently fails to acquire a token rather than erroring
  obviously at deploy time.
- kubenet clusters attempting features that require Azure CNI (some network policy engines, some
  service mesh integrations) — verify CNI mode before assuming a feature is available.
- Subnet sized for Azure CNI pod IPs without accounting for planned scale, requiring a disruptive
  subnet/cluster rebuild later.
