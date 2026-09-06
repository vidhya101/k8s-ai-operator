terraform {
  required_version = ">= 1.6"

  # No backend block = local state. Move to a remote backend deliberately, on purpose, per
  # CLAUDE.md 1.1 ("never silently choose a state backend"):
  #
  #   terraform init -backend-config=../backend-configs/azure.backend.hcl -migrate-state
  #
  # backend "azurerm" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}
