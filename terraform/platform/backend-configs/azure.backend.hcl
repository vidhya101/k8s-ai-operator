# Pair with `backend "azurerm" {}` in versions.tf (uncomment it first).
#
#   az group create --name CHANGE_ME-tfstate-rg --location eastus
#   az storage account create --name CHANGEMEtfstate --resource-group CHANGE_ME-tfstate-rg --sku Standard_LRS --encryption-services blob
#   az storage container create --name tfstate --account-name CHANGEMEtfstate
#
# terraform init -backend-config=backend-configs/azure.backend.hcl -migrate-state

resource_group_name = "CHANGE_ME-tfstate-rg"
storage_account_name = "CHANGEMEtfstate"
container_name        = "tfstate"
key                    = "platform.terraform.tfstate"
