output "api_gateway_url" {
  description = "REST API Gateway base URL"
  value       = module.api_gateway.invoke_url
}

output "lambda_function_names" {
  description = "Lambda function names"
  value       = module.lambda.function_names
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "s3_buckets" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}
