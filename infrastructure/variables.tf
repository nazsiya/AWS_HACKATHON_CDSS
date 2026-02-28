variable "aws_region" {
  description = "AWS region (ap-south-1 for Mumbai, DISHA)"
  type        = string
  default     = "ap-south-1"
}

variable "stage" {
  description = "Deployment stage (dev, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_handlers" {
  description = "Map of Lambda function name -> handler path (api = router for API Gateway)"
  type        = map(string)
  default = {
    api = "cdss.api.handlers.router.handler"
    supervisor = "cdss.api.handlers.supervisor.handler"
    patient    = "cdss.api.handlers.patient.handler"
    surgery    = "cdss.api.handlers.surgery.handler"
    resource   = "cdss.api.handlers.resource.handler"
    scheduling = "cdss.api.handlers.scheduling.handler"
    engagement = "cdss.api.handlers.engagement.handler"
  }
}

variable "lambda_env" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}
