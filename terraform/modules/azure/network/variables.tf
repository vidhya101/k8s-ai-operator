variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "vnet_cidr" {
  type    = string
  default = "10.30.0.0/16"
}

variable "aks_subnet_cidr" {
  type    = string
  default = "10.30.0.0/20"
}

variable "tags" {
  type    = map(string)
  default = {}
}
