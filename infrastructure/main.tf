# CDSS - Clinical Decision Support System
# Terraform: AWS ap-south-1, Serverless-first, DISHA compliant
# Budget target: <$100/month

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
  }
  backend "s3" {
    # Configure via backend config or -backend-config
    # bucket         = "your-cdss-tfstate"
    # key            = "cdss/terraform.tfstate"
    # region         = "ap-south-1"
    # encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = "CDSS"
      ManagedBy = "Terraform"
    }
  }
}

# Lambda (Bedrock Multi-Agent)
module "lambda" {
  source   = "./modules/lambda"
  name     = "cdss"
  stage    = var.stage
  runtime  = "python3.12"
  handlers = var.lambda_handlers
  env      = var.lambda_env
}

# API Gateway REST
module "api_gateway" {
  source         = "./modules/api_gateway"
  name           = "cdss-api"
  stage          = var.stage
  lambda_invoke_arn = module.lambda.invoke_arn
}

# DynamoDB (sessions, medication schedules)
module "dynamodb" {
  source = "./modules/dynamodb"
  name   = "cdss"
  stage  = var.stage
}

# S3 (medical documents, knowledge corpus)
module "s3" {
  source = "./modules/s3"
  name   = "cdss"
  stage  = var.stage
}

# OpenSearch (RAG) - optional; enable if budget allows
# module "opensearch" { ... }

# EventBridge (async inter-agent messaging)
module "eventbridge" {
  source = "./modules/eventbridge"
  name   = "cdss"
  stage  = var.stage
}
