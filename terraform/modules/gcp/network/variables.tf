variable "name" {
  type = string
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/20"
}

variable "pods_cidr" {
  description = "Secondary range for GKE VPC-native Pod IPs"
  type        = string
  default     = "10.20.0.0/14"
}

variable "services_cidr" {
  description = "Secondary range for GKE VPC-native Service IPs"
  type        = string
  default     = "10.24.0.0/20"
}
