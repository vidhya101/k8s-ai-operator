output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "oidc_provider_arn" {
  description = "Feed into modules/aws/irsa to grant an app's ServiceAccount a real IAM role"
  value       = module.eks.oidc_provider_arn
}

output "oidc_provider_url" {
  value = module.eks.oidc_provider_url
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${var.name} --region ${var.aws_region}"
}
