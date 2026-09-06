variable "name" {
  type = string
}

variable "oidc_provider_arn" {
  description = "modules/aws/eks output.oidc_provider_arn"
  type        = string
}

variable "oidc_provider_url" {
  description = "modules/aws/eks output.oidc_provider_url (no https:// prefix)"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace the ServiceAccount lives in"
  type        = string
}

variable "service_account_name" {
  type = string
}

variable "policy_arns" {
  description = "AWS-managed or customer-managed policy ARNs to attach"
  type        = list(string)
  default     = []
}

variable "inline_policy_json" {
  description = "Optional inline policy document (jsonencode(...)) for permissions with no reusable managed policy"
  type        = string
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
