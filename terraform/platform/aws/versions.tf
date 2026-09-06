terraform {
  required_version = ">= 1.6"

  # No backend block = local state. Move to a remote backend deliberately, on purpose, per
  # CLAUDE.md 1.1 ("never silently choose a state backend") — Terraform can't select a backend
  # *type* from a variable, so this is a one-line edit you make yourself:
  #
  #   terraform init -backend-config=../backend-configs/aws.backend.hcl -migrate-state
  #
  # backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
