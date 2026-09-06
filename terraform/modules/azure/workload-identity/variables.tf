variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "oidc_issuer_url" {
  description = "modules/azure/aks output.oidc_issuer_url"
  type        = string
}

variable "namespace" {
  type = string
}

variable "service_account_name" {
  type = string
}

variable "scope" {
  description = "Resource ID (or subscription/resource-group ID) the role_assignments apply to"
  type        = string
}

variable "role_assignments" {
  description = "Built-in or custom RBAC role names, e.g. [\"Storage Blob Data Reader\"]"
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
