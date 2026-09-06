output "cluster_name" {
  value = google_container_cluster.this.name
}

output "cluster_endpoint" {
  value     = google_container_cluster.this.endpoint
  sensitive = true
}

output "cluster_ca_certificate" {
  value     = google_container_cluster.this.master_auth[0].cluster_ca_certificate
  sensitive = true
}

output "workload_pool" {
  description = "Feed into a GSA's IAM policy binding: roles/iam.workloadIdentityUser for `serviceAccount:<workload_pool>[<namespace>/<ksa-name>]`"
  value       = "${var.project_id}.svc.id.goog"
}
