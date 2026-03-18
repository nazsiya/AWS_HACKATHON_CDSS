provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = "CDSS"
      ManagedBy = "Terraform"
    }
  }
}

# Budgets API is only available in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = {
      Project   = "CDSS"
      ManagedBy = "Terraform"
    }
  }
}
