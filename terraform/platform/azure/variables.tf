variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "kubernetes_version" {
  description = "AKS control plane version. No default — pin it explicitly so an upgrade is a deliberate, reviewed change."
  type        = string
}

variable "azure_subscription_id" {
  type = string
}

variable "azure_location" {
  type = string
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

variable "tags" {
  type    = map(string)
  default = {}
}
