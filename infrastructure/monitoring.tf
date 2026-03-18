# CloudWatch dashboards, alarms, and budget guardrails (Phase 12)
# API Gateway latency/4xx/5xx; Lambda duration, errors, throttles; RDS CPU/connections; cost budget.

# ---------------------------------------------------------------------------
# SNS topic for alarm notifications (optional: email subscription)
# ---------------------------------------------------------------------------
resource "aws_sns_topic" "alarms" {
  name = "${local.name_prefix}-alarms"

  tags = {
    Name    = "${local.name_prefix}-alarms"
    Project = var.project_name
  }
}

# ---------------------------------------------------------------------------
# API Gateway REST – alarms (4xx, 5xx, latency)
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${local.name_prefix}-api-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  alarm_description = "API Gateway 5xx errors exceeded threshold"
  alarm_actions     = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-api-5xx"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx" {
  alarm_name          = "${local.name_prefix}-api-4xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 50
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  alarm_description = "API Gateway 4xx errors exceeded threshold (auth/client errors)"
  alarm_actions     = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-api-4xx"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${local.name_prefix}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Average"
  threshold           = 3000
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  alarm_description = "API Gateway average latency > 3s"
  alarm_actions     = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-api-latency"
  }
}

# ---------------------------------------------------------------------------
# Lambda – CDSS API (router) errors and throttles
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "lambda_api_errors" {
  alarm_name          = "${local.name_prefix}-lambda-api-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.cdss_lambda.api_function_name
  }

  alarm_description = "CDSS API Lambda errors"
  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-lambda-api-errors"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_api_throttles" {
  alarm_name          = "${local.name_prefix}-lambda-api-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.cdss_lambda.api_function_name
  }

  alarm_description = "CDSS API Lambda throttles"
  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-lambda-api-throttles"
  }
}

# ---------------------------------------------------------------------------
# RDS Aurora – CPU and database connections
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-aurora-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.aurora.cluster_identifier
  }

  alarm_description = "Aurora cluster CPU > 85%"
  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-aurora-cpu"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name_prefix}-aurora-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.aurora.cluster_identifier
  }

  alarm_description = "Aurora database connections high"
  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions        = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "${local.name_prefix}-aurora-connections"
  }
}

# ---------------------------------------------------------------------------
# CloudWatch dashboard – API Gateway, Lambda, RDS
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "cdss" {
  dashboard_name = "${local.name_prefix}-cdss"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: API Gateway
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway - Request count"
          region = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, { stat = "Sum", period = 60 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway - 4xx/5xx"
          region = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, { stat = "Sum", period = 60 }],
            [".", "5XXError", ".", ".", ".", ".", { stat = "Sum", period = 60 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API Gateway - Latency (ms)"
          region = var.aws_region
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, { stat = "Average", period = 60 }]
          ]
        }
      },
      # Row 2: Lambda CDSS API
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda CDSS API - Invocations & Errors"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", module.cdss_lambda.api_function_name, { stat = "Sum", period = 60 }],
            [".", "Errors", ".", ".", { stat = "Sum", period = 60 }],
            [".", "Throttles", ".", ".", { stat = "Sum", period = 60 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda CDSS API - Duration (ms)"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", module.cdss_lambda.api_function_name, { stat = "Average", period = 60 }],
            [".", ".", ".", ".", { stat = "Maximum", period = 60 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Lambda CDSS API - Concurrent executions"
          region = var.aws_region
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", module.cdss_lambda.api_function_name, { stat = "Maximum", period = 60 }]
          ]
        }
      },
      # Row 3: RDS Aurora
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "Aurora - CPU %"
          region = var.aws_region
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", aws_rds_cluster.aurora.cluster_identifier, { stat = "Average", period = 300 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "Aurora - Database connections"
          region = var.aws_region
          metrics = [
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", aws_rds_cluster.aurora.cluster_identifier, { stat = "Average", period = 300 }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "Aurora - Freeable memory (MB)"
          region = var.aws_region
          metrics = [
            ["AWS/RDS", "FreeableMemory", "DBClusterIdentifier", aws_rds_cluster.aurora.cluster_identifier, { stat = "Average", period = 300 }]
          ]
        }
      }
    ]
  })
}
