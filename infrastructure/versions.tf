terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  # Uncomment and set bucket/key/region for remote state; omit to use local state.
  # backend "s3" {
  #   bucket         = "your-cdss-tfstate"
  #   key            = "cdss/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "cdss-tfstate-lock"
  # }
}
