variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "kubernetes_version" {
  description = "GKE control plane version. No default — pin it explicitly so an upgrade is a deliberate, reviewed change."
  type        = string
}

variable "gcp_project_id" {
  type = string
}

variable "gcp_region" {
  type = string
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

variable "tags" {
  type    = map(string)
  default = {}
}
