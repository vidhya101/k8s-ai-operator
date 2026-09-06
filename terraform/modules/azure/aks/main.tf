# AKS with Azure AD Workload Identity enabled (oidc_issuer + workload_identity) — the Azure
# equivalent of AWS IRSA / GCP Workload Identity. A separately-managed system pool keeps
# kube-system/critical add-ons isolated from application workloads on the "user" pool, mirroring
# the AWS/GCP modules' pattern of a dedicated node group/pool for applications.

resource "azurerm_kubernetes_cluster" "this" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.kubernetes_version

  private_cluster_enabled = var.private_cluster

  oidc_issuer_enabled      = true
  workload_identity_enabled = true

  default_node_pool {
    name                 = "system"
    vm_size              = var.node_vm_size
    vnet_subnet_id       = var.subnet_id
    only_critical_addons_enabled = true
    enable_auto_scaling = true
    min_count            = 1
    max_count            = 3
    os_disk_size_gb      = var.node_os_disk_size_gb
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "azure"
  }

  dynamic "api_server_access_profile" {
    for_each = !var.private_cluster && length(var.authorized_ip_ranges) > 0 ? [1] : []
    content {
      authorized_ip_ranges = var.authorized_ip_ranges
    }
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [default_node_pool[0].min_count, default_node_pool[0].max_count]
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  vm_size               = var.node_vm_size
  vnet_subnet_id        = var.subnet_id
  os_disk_size_gb       = var.node_os_disk_size_gb
  mode                  = "User"

  enable_auto_scaling = true
  min_count            = var.node_min_count
  max_count            = var.node_max_count

  tags = var.tags

  lifecycle {
    ignore_changes = [min_count, max_count] # let the Cluster Autoscaler own steady-state sizing after initial provisioning
  }
}
