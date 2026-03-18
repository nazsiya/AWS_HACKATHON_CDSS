# CDSS - Clinical Decision Support System
# Single REST API: /health, /api/v1/{proxy+} → CDSS router Lambda (patients, surgeries, resources, schedule, engagement, hospitals, severity assessment).
# Storage: RDS Aurora + S3 only (no DynamoDB per implementation plan).

# CDSS Multi-Agent Lambda (api = router, supervisor, patient, surgery, resource, scheduling, engagement)
resource "aws_lambda_layer_version" "python_deps" {
  filename            = "layer.zip"
  layer_name          = "${local.name_prefix}-python-deps"
  compatible_runtimes = ["python3.12", "python3.11", "python3.10"]
  source_code_hash    = filebase64sha256("layer.zip")
}

module "cdss_lambda" {
  source                = "./modules/lambda"
  name                  = "cdss"
  stage                 = local.stage
  runtime               = "python3.12"
  handlers              = var.lambda_handlers
  env                   = merge(var.lambda_env, {
    RDS_CONFIG_SECRET_NAME     = aws_secretsmanager_secret.rds_config.name
    BEDROCK_CONFIG_SECRET_NAME = aws_secretsmanager_secret.bedrock_config.name
    S3_BUCKET_MAIN             = aws_s3_bucket.main.id
    S3_BUCKET_DOCUMENTS        = aws_s3_bucket.documents.id
    S3_BUCKET_CORPUS           = aws_s3_bucket.corpus.id
    EVENT_BUS_NAME             = module.cdss_eventbridge.event_bus_name
    SQS_AGENT_EVENTS_URL       = aws_sqs_queue.agent_events.id
    COGNITO_USER_POOL_ID       = aws_cognito_user_pool.main.id
    SNS_TOPIC_DOCTOR_ESCALATIONS_ARN = aws_sns_topic.doctor_escalations.arn
    SNS_TOPIC_PATIENT_REMINDERS_ARN  = aws_sns_topic.patient_reminders.arn
    USE_AGENTCORE              = var.use_agentcore ? "true" : "false"
    AGENT_RUNTIME_ARN          = var.agent_runtime_arn
    DB_CONNECT_TIMEOUT         = "10"
  })
  attach_bedrock_policy  = true
  bedrock_policy_arn     = aws_iam_policy.bedrock_invoke.arn
  layers                 = [aws_lambda_layer_version.python_deps.arn]

  vpc_subnet_ids         = var.enable_lambda_vpc ? [aws_subnet.private_a.id, aws_subnet.private_b.id] : []
  vpc_security_group_ids = var.enable_lambda_vpc ? [aws_security_group.lambda.id] : []
}

# Attach CDSS services policy (Secrets Manager, SSM, EventBridge, SQS, S3) to Lambda role
resource "aws_iam_role_policy_attachment" "cdss_lambda_services" {
  role       = module.cdss_lambda.role_name
  policy_arn = aws_iam_policy.cdss_lambda_services.arn
}

# Attach AgentCore Runtime invoke policy when use_agentcore is true (docs/agentcore-next-steps-implementation.md)
resource "aws_iam_role_policy_attachment" "cdss_lambda_agentcore" {
  count = var.use_agentcore ? 1 : 0

  role       = module.cdss_lambda.role_name
  policy_arn = aws_iam_policy.bedrock_agentcore_invoke[0].arn
}


# EventBridge: async inter-agent messaging
module "cdss_eventbridge" {
  source = "./modules/eventbridge"
  name   = "cdss"
  stage  = local.stage

  # Map of agent keys to their corresponding Lambda function metadata for routing
  agent_lambdas = {
    for k, v in var.lambda_handlers : k => {
      function_name = module.cdss_lambda.function_names_map[k]
      arn           = module.cdss_lambda.function_arns_map[k]
    }
    if k != "api" && k != "agent_worker" && k != "supervisor" # Exclude non-target agents
  }
}
