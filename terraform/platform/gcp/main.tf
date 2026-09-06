locals {
  common_labels = merge(var.tags, {
    environment = var.environment
    managed-by  = "terraform"
    project     = var.name
  })
}

module "network" {
  source = "../../modules/gcp/network"

  name       = var.name
  project_id = var.gcp_project_id
  region     = var.gcp_region
}

module "gke" {
  source = "../../modules/gcp/gke"

  cluster_name        = var.name
  project_id          = var.gcp_project_id
  region              = var.gcp_region
  kubernetes_version  = var.kubernetes_version
  network_id          = module.network.network_id
  subnetwork_name     = module.network.subnetwork_name
  pods_range_name     = module.network.pods_range_name
  services_range_name = module.network.services_range_name
  node_machine_type   = var.node_machine_type
  node_min_count      = var.node_min_count
  node_max_count      = var.node_max_count
  labels              = local.common_labels
}
