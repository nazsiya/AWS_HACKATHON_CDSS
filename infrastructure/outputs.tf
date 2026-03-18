output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.main.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.main.arn
}

output "aurora_cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.aurora.endpoint
}

output "aurora_cluster_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.aurora.reader_endpoint
}

output "aurora_database_name" {
  description = "Aurora database name"
  value       = aws_rds_cluster.aurora.database_name
}

output "bedrock_policy_arn" {
  description = "IAM policy ARN for Bedrock invocation"
  value       = aws_iam_policy.bedrock_invoke.arn
}

output "api_gateway_url" {
  description = "Base URL of the REST API Gateway"
  value       = aws_api_gateway_stage.main.invoke_url
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_staff_client_id" {
  description = "ID of the Staff App Client"
  value       = aws_cognito_user_pool_client.staff_app.id
}

output "cognito_patient_client_id" {
  description = "ID of the Patient Portal Client"
  value       = aws_cognito_user_pool_client.patient_portal.id
}

output "websocket_url" {
  description = "URL of the WebSocket API"
  value       = var.enable_websocket_api ? aws_apigatewayv2_stage.websocket[0].invoke_url : ""
}

output "staff_app_cf_url" {
  description = "URL of the Staff Web App CloudFront Distribution"
  value       = aws_cloudfront_distribution.staff_app.domain_name
}

output "staff_app_cf_id" {
  description = "CloudFront distribution ID for Staff Web App (use for invalidations)"
  value       = aws_cloudfront_distribution.staff_app.id
}

output "patient_portal_cf_url" {
  description = "URL of the Patient Portal CloudFront Distribution"
  value       = aws_cloudfront_distribution.patient_portal.domain_name
}

output "patient_portal_cf_id" {
  description = "CloudFront distribution ID for Patient Portal"
  value       = aws_cloudfront_distribution.patient_portal.id
}

output "rds_endpoint" {
  value = aws_rds_cluster.aurora.endpoint
}

output "bedrock_config_secret_name" {
  description = "Secrets Manager secret name for Bedrock config"
  value       = aws_secretsmanager_secret.bedrock_config.name
}

output "rds_config_secret_name" {
  description = "Secrets Manager secret name for RDS connection config (IAM auth)"
  value       = aws_secretsmanager_secret.rds_config.name
}


output "api_gateway_health_url" {
  description = "API Gateway health check URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/health"
}

# CDSS
output "api_gateway_cdss_url" {
  description = "CDSS API base URL (proxy)"
  value       = "${aws_api_gateway_stage.main.invoke_url}/api/"
}

output "cdss_lambda_function_names" {
  description = "CDSS Lambda function names"
  value       = module.cdss_lambda.function_names
}


output "cdss_event_bus_name" {
  description = "CDSS EventBridge event bus name"
  value       = module.cdss_eventbridge.event_bus_name
}

output "s3_bucket_documents" {
  description = "S3 bucket for medical documents"
  value       = aws_s3_bucket.documents.id
}

output "s3_bucket_corpus" {
  description = "S3 bucket for knowledge corpus"
  value       = aws_s3_bucket.corpus.id
}

# AgentCore Gateway – Lambda ARN for setup_agentcore_gateway.py (docs/agentcore-gateway-manual-steps.md)
output "gateway_get_hospitals_lambda_arn" {
  description = "ARN of the Gateway tool Lambda (get_hospitals, get_ot_status, get_abdm_record stub)"
  value       = aws_lambda_function.gateway_tools.arn
}

# Monitoring (Phase 12)
output "cloudwatch_dashboard_name" {
  description = "CloudWatch dashboard name for CDSS metrics"
  value       = aws_cloudwatch_dashboard.cdss.dashboard_name
}

output "alarms_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications (subscribe email for alerts)"
  value       = aws_sns_topic.alarms.arn
}
