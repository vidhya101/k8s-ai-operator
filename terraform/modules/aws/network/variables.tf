variable "name" {
  description = "Prefix applied to every resource this module creates"
  type        = string
}

variable "cidr_block" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Availability zones to spread subnets across. 3 AZs is the resilience floor for a production EKS control plane / node spread; 1-2 is fine for dev."
  type        = list(string)
}

variable "single_nat_gateway" {
  description = <<-EOT
    true = one shared NAT Gateway for all private subnets (cheaper: ~$32/mo instead of ~$32/mo
    per AZ; the tradeoff is that a single NAT Gateway's AZ failing takes egress down for every
    private subnet). Default true because most environments using this template are cost-sensitive
    dev/staging/home-lab (see .claude/config/environment.md's AWS budget guardrail) — set false
    explicitly for a production environment that needs per-AZ NAT redundancy.
  EOT
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
