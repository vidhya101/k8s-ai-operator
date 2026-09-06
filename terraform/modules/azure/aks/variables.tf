variable "cluster_name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "kubernetes_version" {
  description = "Do not default this silently — pin per environment.tfvars (same reasoning as the AWS/GCP modules' variable of the same name)."
  type        = string
}

variable "subnet_id" {
  type = string
}

variable "private_cluster" {
  type    = bool
  default = true
}

variable "authorized_ip_ranges" {
  description = "CIDR allowlist for the public API server endpoint. Only used when private_cluster = false."
  type        = list(string)
  default     = []
}

variable "node_vm_size" {
  type    = string
  default = "Standard_D4s_v5"
}

variable "node_min_count" {
  type    = number
  default = 2
}

variable "node_max_count" {
  type    = number
  default = 5
}

variable "node_os_disk_size_gb" {
  type    = number
  default = 100
}

variable "tags" {
  type    = map(string)
  default = {}
}
