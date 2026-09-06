# Pair with `backend "gcs" {}` in versions.tf (uncomment it first).
#
#   gcloud storage buckets create gs://CHANGE_ME-tfstate --location=us-central1 --uniform-bucket-level-access
#   gcloud storage buckets update gs://CHANGE_ME-tfstate --versioning
#
# terraform init -backend-config=backend-configs/gcp.backend.hcl -migrate-state

bucket = "CHANGE_ME-tfstate"
prefix = "platform"
