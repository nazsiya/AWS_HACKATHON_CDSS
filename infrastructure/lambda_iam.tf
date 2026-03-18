# IAM policy for CDSS Lambda: Secrets Manager, SSM, EventBridge, SQS, S3
# Attached to the CDSS Lambda execution role so agents can read config and use event/data stores.

data "aws_caller_identity" "iam_current" {}
data "aws_region" "current" {}

resource "aws_iam_policy" "cdss_lambda_services" {
  name        = "${local.name_prefix}-lambda-services"
  description = "CDSS Lambda: Secrets Manager, SSM, EventBridge, SQS, S3 access for agents"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManager"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.rds_config.arn,
          aws_secretsmanager_secret.bedrock_config.arn
        ]
      },
      {
        Sid    = "SSMParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.iam_current.account_id}:parameter/cdss/*"
      },
      {
        Sid    = "RDSConnect"
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = "arn:aws:rds-db:${data.aws_region.current.name}:${data.aws_caller_identity.iam_current.account_id}:dbuser:*/${var.db_username}"
      },
      {
        Sid    = "SSMAdminConfigWrite"
        Effect = "Allow"
        Action = [
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.iam_current.account_id}:parameter/cdss/admin/config"
      },
      {
        Sid    = "CognitoListUsers"
        Effect = "Allow"
        Action = [
          "cognito-idp:ListUsers"
        ]
        Resource = aws_cognito_user_pool.main.arn
      },
      {
        Sid    = "EventBridgePutEvents"
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = module.cdss_eventbridge.event_bus_arn
      },
      {
        Sid    = "SQSAgentEvents"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.agent_events.arn
      },
      {
        Sid    = "S3MainBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
      },
      {
        Sid    = "S3DocumentsBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      },
      {
        Sid    = "S3CorpusBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.corpus.arn,
          "${aws_s3_bucket.corpus.arn}/*"
        ]
      },
      {
        Sid    = "SNSDoctorEscalations"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.doctor_escalations.arn
      }
      ,
      {
        Sid    = "SNSPatientReminders"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.patient_reminders.arn
      }
    ]
  })
}
