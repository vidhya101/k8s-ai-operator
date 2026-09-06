output "cluster_name" {
  value = module.aks.cluster_name
}

output "oidc_issuer_url" {
  description = "Feed into modules/azure/workload-identity to federate a User Assigned Managed Identity to a Kubernetes ServiceAccount"
  value       = module.aks.oidc_issuer_url
}

output "kubeconfig_command" {
  value = "az aks get-credentials --name ${var.name} --resource-group ${var.name}-rg"
}
