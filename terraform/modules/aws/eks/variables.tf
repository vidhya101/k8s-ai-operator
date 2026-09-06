variable "cluster_name" {
  type = string
}

variable "kubernetes_version" {
  description = "EKS control plane version. Do not default this silently across environments — pin it explicitly per environment.tfvars so a prod upgrade is always a deliberate, reviewed change."
  type        = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  description = "Worker nodes and the (recommended private-only) control plane ENIs live here"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Only used if endpoint_public_access = true and you want a public-facing surface; otherwise unused"
  type        = list(string)
  default     = []
}

variable "endpoint_public_access" {
  description = "false = API server reachable only from inside the VPC (bastion/VPN/peered network). true = also reachable from the internet, narrowed by endpoint_public_access_cidrs."
  type        = bool
  default     = false
}

variable "endpoint_public_access_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 5
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT"
  type        = string
  default     = "ON_DEMAND"
}

variable "enable_cluster_encryption" {
  description = "Encrypt Kubernetes Secrets at rest with a customer-managed KMS key (in addition to EBS/etcd's own encryption) — the extra layer that specifically covers `kubectl get secret`-visible data."
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
