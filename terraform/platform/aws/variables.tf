variable "name" {
  description = "Prefix applied to every resource this creates (cluster name, VPC name, IAM roles, ...)"
  type        = string
}

variable "environment" {
  description = "dev | staging | prod | ... — applied as a tag everywhere"
  type        = string
}

variable "kubernetes_version" {
  description = "EKS control plane version. No default — pin it explicitly so an upgrade is a deliberate, reviewed change."
  type        = string
}

variable "aws_region" {
  type = string
}

variable "aws_azs" {
  description = "3 AZs is the resilience floor for production; 1-2 is fine for dev."
  type        = list(string)
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
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
