# Azure AD Workload Identity: a User Assigned Managed Identity federated to a specific Kubernetes
# ServiceAccount (namespace + name) via the AKS cluster's OIDC issuer — no client secret/cert
# stored anywhere. The resulting client_id is what goes into serviceAccountAnnotations in an
# AppWorkload CR, or the `azure.workload.identity/client-id` patch in
# k8s/app/overlays/azure/kustomization.yaml.

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

resource "azurerm_user_assigned_identity" "this" {
  name                = "${var.name}-workload-identity"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "this" {
  name                = "${var.name}-federated-credential"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.this.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = var.oidc_issuer_url
  subject             = "system:serviceaccount:${var.namespace}:${var.service_account_name}"
}

resource "azurerm_role_assignment" "this" {
  for_each             = toset(var.role_assignments)
  scope                = var.scope
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}
