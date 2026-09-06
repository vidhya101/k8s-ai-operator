variable "cluster_name" {
  type = string
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "kubernetes_version" {
  description = "Do not default this silently — pin per environment.tfvars so a prod upgrade is a deliberate change (see terraform/modules/aws/eks's variable of the same name for the same reasoning)."
  type        = string
}

variable "network_id" {
  type = string
}

variable "subnetwork_name" {
  type = string
}

variable "pods_range_name" {
  type = string
}

variable "services_range_name" {
  type = string
}

variable "private_cluster" {
  description = "true = nodes have no public IPs; the control plane endpoint is still reachable per master_authorized_networks"
  type        = bool
  default     = true
}

variable "master_authorized_networks" {
  description = "CIDR allowlist for control-plane API access. Empty = only Google-internal access paths (Cloud Shell won't work; use a bastion/VPN CIDR here for real access)."
  type        = list(object({ cidr_block = string, display_name = string }))
  default     = []
}

variable "node_machine_type" {
  type    = string
  default = "e2-standard-4"
}

variable "node_min_count" {
  type    = number
  default = 2
}

variable "node_max_count" {
  type    = number
  default = 5
}

variable "node_disk_size_gb" {
  type    = number
  default = 100
}

variable "labels" {
  type    = map(string)
  default = {}
}
