# AgentCore Gateway tool Lambda – invoked by Bedrock AgentCore Gateway as MCP tool target.
# See docs/agentcore-gateway-manual-steps.md and docs/agentcore-next-steps-implementation.md.

data "archive_file" "gateway_tools" {
  type        = "zip"
  source_dir  = "${path.module}/gateway_tools_src"
  output_path = "${path.module}/gateway_tools.zip"
}

resource "aws_iam_role" "gateway_tools" {
  name = "${local.name_prefix}-gateway-tools-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "gateway_tools_basic" {
  role       = aws_iam_role.gateway_tools.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "gateway_tools_vpc" {
  role       = aws_iam_role.gateway_tools.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_policy" "gateway_tools_services" {
  name        = "${local.name_prefix}-gateway-tools-services"
  description = "Permissions for Gateway tools to access Secrets Manager and RDS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.rds_config.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["rds-db:connect"]
        Resource = ["arn:aws:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${aws_rds_cluster.aurora.cluster_resource_id}/${var.db_username}"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "gateway_tools_services" {
  role       = aws_iam_role.gateway_tools.name
  policy_arn = aws_iam_policy.gateway_tools_services.arn
}

resource "aws_lambda_function" "gateway_tools" {
  filename         = data.archive_file.gateway_tools.output_path
  function_name    = "${local.name_prefix}-gateway-get-hospitals"
  role             = aws_iam_role.gateway_tools.arn
  handler          = "lambda_handler.handler"
  source_code_hash = data.archive_file.gateway_tools.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256 # Increased for DB queries

  environment {
    variables = {
      RDS_CONFIG_SECRET_NAME = aws_secretsmanager_secret.rds_config.name
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }
}
