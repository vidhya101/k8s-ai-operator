terraform {
  required_version = ">= 1.6"

  # No backend block = local state. Move to a remote backend deliberately, on purpose, per
  # CLAUDE.md 1.1 ("never silently choose a state backend"):
  #
  #   terraform init -backend-config=../backend-configs/gcp.backend.hcl -migrate-state
  #
  # backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
