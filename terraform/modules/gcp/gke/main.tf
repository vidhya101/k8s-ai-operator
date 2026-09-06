# GKE Standard (not Autopilot — Autopilot doesn't allow the node-level hardening this template's
# k8s/app/base manifests assume, e.g. custom securityContext/seccompProfile enforcement points).
# Workload Identity is enabled unconditionally: it's the GCP equivalent of AWS IRSA and there's no
# good reason to run a modern GKE cluster without it.

resource "google_container_cluster" "this" {
  name     = var.cluster_name
  project  = var.project_id
  location = var.region

  # Separately-managed node pool below — the cluster's own default pool is deleted immediately
  # after creation, which is Google's documented pattern for controlling node pool config fully.
  remove_default_node_pool = true
  initial_node_count       = 1

  networking_mode = "VPC_NATIVE"
  network         = var.network_id
  subnetwork      = var.subnetwork_name
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_range_name
    services_secondary_range_name = var.services_range_name
  }

  release_channel {
    channel = "REGULAR"
  }
  min_master_version = var.kubernetes_version

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # NetworkPolicy enforcement (Calico under the hood) — required for k8s/app/base/networkpolicy.yaml
  # to actually do anything on GKE; it isn't on by default the way EKS's VPC CNI generally is.
  network_policy {
    enabled  = true
    provider = "CALICO"
  }

  dynamic "private_cluster_config" {
    for_each = var.private_cluster ? [1] : []
    content {
      enable_private_nodes    = true
      enable_private_endpoint = false # control plane endpoint still reachable per master_authorized_networks_config below
      master_ipv4_cidr_block  = "172.16.0.0/28"
    }
  }

  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS", "APISERVER"]
  }
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
  }

  resource_labels = var.labels
}

resource "google_container_node_pool" "default" {
  name     = "${var.cluster_name}-default"
  project  = var.project_id
  location = var.region
  cluster  = google_container_cluster.this.name

  autoscaling {
    min_node_count = var.node_min_count
    max_node_count = var.node_max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = var.node_machine_type
    disk_size_gb = var.node_disk_size_gb
    disk_type    = "pd-ssd"

    # Workload Identity binding at the node-pool level — pairs with a Kubernetes-side
    # `iam.gke.io/gcp-service-account` annotation on the ServiceAccount (see
    # k8s/app/overlays/gcp/kustomization.yaml) to federate a KSA to a real GSA, no downloaded key.
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"] # actual permissions come from IAM on the node SA + Workload Identity, not from these legacy scopes

    labels = var.labels
  }

  lifecycle {
    ignore_changes = [autoscaling[0].min_node_count, autoscaling[0].max_node_count] # let Cluster Autoscaler own steady-state sizing after initial provisioning
  }
}
