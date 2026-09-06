# Pair with `backend "s3" {}` in versions.tf (uncomment it first). Create the bucket + lock table
# once, out-of-band, before pointing Terraform at them (chicken-and-egg: state storage can't
# bootstrap itself from the same state it's storing).
#
#   aws s3api create-bucket --bucket CHANGE_ME-tfstate --region us-east-1
#   aws s3api put-bucket-versioning --bucket CHANGE_ME-tfstate --versioning-configuration Status=Enabled
#   aws dynamodb create-table --table-name CHANGE_ME-tf-locks --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
#
# terraform init -backend-config=backend-configs/aws.backend.hcl -migrate-state

bucket         = "CHANGE_ME-tfstate"
key            = "platform/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "CHANGE_ME-tf-locks"
encrypt        = true
