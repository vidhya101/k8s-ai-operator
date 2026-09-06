locals {
  common_tags = merge(var.tags, {
    environment = var.environment
    managed-by  = "terraform"
    project     = var.name
  })
}

module "network" {
  source = "../../modules/aws/network"

  name = var.name
  azs  = var.aws_azs
  tags = local.common_tags
}

module "eks" {
  source = "../../modules/aws/eks"

  cluster_name        = var.name
  kubernetes_version  = var.kubernetes_version
  vpc_id              = module.network.vpc_id
  private_subnet_ids  = module.network.private_subnet_ids
  node_instance_types = var.node_instance_types
  node_min_size       = var.node_min_count
  node_desired_size   = var.node_min_count
  node_max_size       = var.node_max_count
  tags                = local.common_tags
}
