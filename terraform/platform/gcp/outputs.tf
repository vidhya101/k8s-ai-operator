output "cluster_name" {
  value = module.gke.cluster_name
}

output "cluster_endpoint" {
  value     = module.gke.cluster_endpoint
  sensitive = true
}

output "workload_pool" {
  description = "Feed into a GSA's Workload Identity IAM binding (roles/iam.workloadIdentityUser)"
  value       = module.gke.workload_pool
}

output "kubeconfig_command" {
  value = "gcloud container clusters get-credentials ${var.name} --region ${var.gcp_region} --project ${var.gcp_project_id}"
}
