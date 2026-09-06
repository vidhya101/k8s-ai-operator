locals {
  common_tags = merge(var.tags, {
    environment = var.environment
    managed-by  = "terraform"
    project     = var.name
  })
}

module "network" {
  source = "../../modules/azure/network"

  name                = var.name
  location            = var.azure_location
  resource_group_name = "${var.name}-rg"
  tags                = local.common_tags
}

module "aks" {
  source = "../../modules/azure/aks"

  cluster_name        = var.name
  resource_group_name = module.network.resource_group_name
  location            = module.network.location
  kubernetes_version  = var.kubernetes_version
  subnet_id           = module.network.aks_subnet_id
  node_vm_size        = var.node_vm_size
  node_min_count      = var.node_min_count
  node_max_count      = var.node_max_count
  tags                = local.common_tags
}
