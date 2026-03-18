# Project and region (default ap-south-1 for Mumbai/DISHA data residency)
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cdss"
}

variable "aws_region" {
  description = "AWS region for deployment (ap-south-1 for DISHA compliance)"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# RDS / Aurora
variable "db_username" {
  description = "Master username for Aurora"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Master password for Aurora"
  type        = string
  sensitive   = true
}


# Bedrock (CDSS agents)
variable "bedrock_agent_id" {
  description = "Bedrock Agent ID (optional; empty = use Converse API for CDSS)"
  type        = string
  default     = ""
}

variable "bedrock_agent_alias_id" {
  description = "Bedrock Agent Alias ID"
  type        = string
  default     = "TSTALIASID"
}

variable "bedrock_model_id" {
  description = "Bedrock model for Converse/chat (e.g. apac.amazon.nova-lite-v1:0 in ap-south-1)"
  type        = string
  default     = "apac.amazon.nova-lite-v1:0"
}

# CDSS Lambda (multi-agent) - handlers and env
variable "lambda_handlers" {
  description = "Map of Lambda function name -> handler path (api = router for API Gateway)"
  type        = map(string)
  default = {
    api           = "cdss.api.handlers.router.handler"
    agent_worker  = "cdss.mcp.consumer.handler"
    supervisor    = "cdss.api.handlers.supervisor.handler"
    patient       = "cdss.api.handlers.patient.handler"
    surgery    = "cdss.api.handlers.surgery.handler"
    resource   = "cdss.api.handlers.resource.handler"
    scheduling = "cdss.api.handlers.scheduling.handler"
    engagement = "cdss.api.handlers.engagement.handler"
  }
}

variable "lambda_env" {
  description = "Environment variables for CDSS Lambda functions"
  type        = map(string)
  default     = {}
}

# Cognito
variable "cognito_user_pool_name" {
  description = "Name of the Cognito User Pool"
  type        = string
  default     = "cdss-user-pool"
}

# Require Cognito on /api routes. Set false for local dev without Cognito (e.g. Postman).
variable "api_require_cognito" {
  description = "Require Cognito User Pools authorizer on /api routes"
  type        = bool
  default     = true
}

# WebSocket API
variable "enable_websocket_api" {
  description = "Deploy WebSocket API for real-time updates"
  type        = bool
  default     = true
}

variable "enable_websocket_authorizer" {
  description = "Require JWT (Cognito) authorizer on WebSocket $connect. Set false for local testing without auth."
  type        = bool
  default     = true
}

variable "websocket_connections_table_name" {
  description = "Reserved for future: RDS table name for WebSocket connection IDs (Phase 4). Currently unused; WebSocket is stateless."
  type        = string
  default     = "cdss-websocket-connections"
}

# Lambda VPC (for RDS access). When true, Lambdas run in private subnets with NAT for Bedrock.
variable "enable_lambda_vpc" {
  description = "Attach Lambdas to VPC so they can reach RDS (private subnets); NAT allows Bedrock"
  type        = bool
  default     = true
}

# Frontend / CloudFront
variable "staff_app_domain" {
  description = "Domain name for the Staff Web App (if any)"
  type        = string
  default     = ""
}

variable "patient_portal_domain" {
  description = "Domain name for the Patient Portal (if any)"
  type        = string
  default     = ""
}

# AI Layer
variable "enable_transcribe" {
  description = "Enable Amazon Transcribe permissions for agents"
  type        = bool
  default     = true
}

variable "enable_translate" {
  description = "Enable Amazon Translate permissions for agents"
  type        = bool
  default     = true
}

# AgentCore (Bedrock AgentCore Runtime) – per docs/agentcore-implementation-plan.md
variable "use_agentcore" {
  description = "When true, Lambda may invoke AgentCore Runtime (e.g. for /hospitals); requires agent_runtime_arn"
  type        = bool
  default     = false
}

variable "agent_runtime_arn" {
  description = "ARN of the deployed AgentCore Runtime (set after 'agentcore deploy' from agentcore/agent/)"
  type        = string
  default     = ""
}

# Monitoring & cost (Phase 12)
variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD for budget alerts (e.g. 100); set 0 to disable budget"
  type        = number
  default     = 100
}

variable "budget_notification_emails" {
  description = "Email addresses for budget alerts (80%% and 100%% actual/forecasted). At least one required when monthly_budget_usd > 0."
  type        = list(string)
  default     = ["your-email@example.com"]
}

# Bastion SSH (optional – per reference/docs/infrastructure/bastion-setup.md)
# When set, opens port 22 from your IP so you can use SSH tunnel instead of SSM.
variable "bastion_ssh_public_key" {
  description = "SSH public key for bastion (e.g. from cat ~/.ssh/id_rsa.pub). If set, enables SSH tunnel; leave empty for SSM-only."
  type        = string
  default     = ""
  sensitive   = true
}

variable "bastion_allowed_cidr" {
  description = "Your IP in CIDR for bastion SSH (e.g. 203.0.113.42/32). Use with bastion_ssh_public_key."
  type        = string
  default     = ""
}
