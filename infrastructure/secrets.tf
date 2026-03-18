# Bedrock config - region, model_id. No credentials stored here.
# AWS credentials use the default chain (IAM role, aws configure).
resource "aws_secretsmanager_secret" "bedrock_config" {
  name        = "${local.name_prefix}/bedrock-config"
  description = "Bedrock configuration (region, model_id)"

  tags = {
    Name    = "${local.name_prefix}-bedrock-config"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "bedrock_config" {
  secret_id = aws_secretsmanager_secret.bedrock_config.id
  secret_string = jsonencode({
    region   = var.aws_region
    model_id = var.bedrock_model_id
  })
}

# RDS connection config for IAM auth - no password stored. Use boto3 generate_db_auth_token.
# One-time: connect with password and run: GRANT rds_iam TO <db_username>;
resource "aws_secretsmanager_secret" "rds_config" {
  name        = "${local.name_prefix}/rds-config"
  description = "RDS connection config (host, port, database, username) for IAM auth"

  tags = {
    Name    = "${local.name_prefix}-rds-config"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "rds_config" {
  secret_id = aws_secretsmanager_secret.rds_config.id
  secret_string = jsonencode({
    host     = aws_rds_cluster.aurora.endpoint
    port     = 5432
    database = aws_rds_cluster.aurora.database_name
    username = var.db_username
    region   = var.aws_region
  })
}
