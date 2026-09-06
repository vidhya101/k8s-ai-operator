---
name: azure
description: Azure-specific cloud engineering — management groups/subscriptions, Entra ID (Azure AD), VNet design, and RBAC. Use when the target cloud is Azure and the question isn't specific to Terraform/AKS (see those skills for IaC/K8s specifics on Azure).
---

# Azure

General Azure cloud-engineering reference. Pair with `terraform` for provisioning and `aks` for Kubernetes.

## Subscription & Management Group Structure

- Management groups → subscriptions (per environment or per team) → resource groups as the hierarchy for
  policy inheritance and billing/blast-radius isolation.
- Azure Policy assigned at the management group or subscription level for guardrails (e.g. require
  encryption, restrict allowed regions/SKUs) that apply regardless of RBAC grants.
- Resource groups scoped to a logical lifecycle unit (a single app's resources that get created/destroyed
  together) rather than one giant resource group per subscription.

## Identity: Entra ID (Azure AD)

- Managed identities (system- or user-assigned) for Azure resources talking to other Azure services —
  avoid service principal client secrets where a managed identity can do the job.
- Workload Identity Federation for AKS pods and for CI (GitHub OIDC → Azure AD federated credential) —
  see `aks` and `github-actions` skills.
- RBAC assignments scoped to the resource/resource-group/subscription level that actually needs it, using
  built-in roles before creating custom roles.

## Networking

- VNet per environment (or per subscription); plan address space to avoid overlap before VNet peering or
  a hub-spoke topology is needed.
- NSGs (Network Security Groups) as the primary segmentation tool at the subnet/NIC level; Azure Firewall
  or a hub VNet's firewall for centralized egress control in a hub-spoke design.
- Private Endpoints for PaaS services (Storage, SQL, Key Vault) to keep traffic off the public internet
  instead of relying solely on firewall rules on the public endpoint.

## Key CLI

```bash
az account show                                  # confirm active subscription
az account list --output table
az group list --output table
az network vnet list / az network nsg list
az role assignment list --scope <resource-id>
az monitor activity-log list                      # Azure's audit trail equivalent to CloudTrail
```

## Common Pitfalls

- Overly broad RBAC (`Owner` or `Contributor` at the subscription level) granted to unblock a task instead
  of a scoped custom or built-in role.
- Resources left with public network access enabled on a PaaS service (Storage account, SQL server) when
  a Private Endpoint was intended but not enforced (`publicNetworkAccess` not actually disabled).
- Azure Policy assignments that are `Audit` mode when the intent was `Deny` — audit-only doesn't block
  the non-compliant resource from being created.
