resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.name_prefix}-api"
  description = "CDSS API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "${local.name_prefix}-api"
    Project     = var.project_name
    Environment = var.environment
  }
}

# /api -> CDSS router Lambda (proxy)
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

resource "aws_api_gateway_resource" "api_proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "api_proxy_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.api_proxy.id
  http_method   = "ANY"
  authorization = var.api_require_cognito ? "COGNITO_USER_POOLS" : "NONE"
  authorizer_id = var.api_require_cognito ? aws_api_gateway_authorizer.cognito.id : null
  request_parameters = {
    "method.request.path.proxy" = true
  }
}

resource "aws_api_gateway_integration" "api_proxy" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.api_proxy.id
  http_method             = aws_api_gateway_method.api_proxy_any.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.cdss_lambda.invoke_arn
}

# OPTIONS /api/{proxy+} (CORS preflight) must be unauthenticated even when ANY is Cognito-protected.
resource "aws_api_gateway_method" "api_proxy_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.api_proxy.id
  http_method   = "OPTIONS"
  authorization = "NONE"
  request_parameters = {
    "method.request.path.proxy" = true
  }
}

resource "aws_api_gateway_integration" "api_proxy_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.api_proxy.id
  http_method = aws_api_gateway_method.api_proxy_options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "api_proxy_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.api_proxy.id
  http_method = aws_api_gateway_method.api_proxy_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "api_proxy_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.api_proxy.id
  http_method = aws_api_gateway_method.api_proxy_options.http_method
  status_code = aws_api_gateway_method_response.api_proxy_options_200.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

resource "aws_lambda_permission" "cdss_api_gateway" {
  statement_id  = "AllowAPIGatewayInvokeCDSS"
  action        = "lambda:InvokeFunction"
  function_name = module.cdss_lambda.api_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*/api/*"
}

# Allow API Gateway to invoke CDSS Lambda for GET /dashboard
resource "aws_lambda_permission" "cdss_api_gateway_dashboard" {
  statement_id  = "AllowAPIGatewayInvokeCDSSDashboard"
  action        = "lambda:InvokeFunction"
  function_name = module.cdss_lambda.api_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/GET/dashboard"
}

# Allow API Gateway to invoke CDSS Lambda for POST /agent
resource "aws_lambda_permission" "cdss_api_gateway_agent" {
  statement_id  = "AllowAPIGatewayInvokeCDSSAgent"
  action        = "lambda:InvokeFunction"
  function_name = module.cdss_lambda.api_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/POST/agent"
}

# Allow API Gateway to invoke CDSS Lambda for GET /health (production alignment: same contract as local)
resource "aws_lambda_permission" "cdss_api_gateway_health" {
  statement_id  = "AllowAPIGatewayInvokeCDSSHealth"
  action        = "lambda:InvokeFunction"
  function_name = module.cdss_lambda.api_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/GET/health"
}


resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {}
}

resource "aws_api_gateway_integration" "health_mock" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.cdss_lambda.invoke_arn
}

# OPTIONS /health (CORS preflight)
resource "aws_api_gateway_method" "health_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "health_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "health_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  status_code = aws_api_gateway_method_response.health_options_200.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

# GET /dashboard -> CDSS router Lambda (same auth as /api)
resource "aws_api_gateway_resource" "dashboard" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "dashboard"
}

resource "aws_api_gateway_method" "dashboard_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.dashboard.id
  http_method   = "GET"
  authorization = var.api_require_cognito ? "COGNITO_USER_POOLS" : "NONE"
  authorizer_id = var.api_require_cognito ? aws_api_gateway_authorizer.cognito.id : null
}

resource "aws_api_gateway_integration" "dashboard" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.dashboard.id
  http_method             = aws_api_gateway_method.dashboard_get.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.cdss_lambda.invoke_arn
}

# OPTIONS /dashboard (CORS preflight)
resource "aws_api_gateway_method" "dashboard_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.dashboard.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "dashboard_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dashboard.id
  http_method = aws_api_gateway_method.dashboard_options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "dashboard_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dashboard.id
  http_method = aws_api_gateway_method.dashboard_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "dashboard_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.dashboard.id
  http_method = aws_api_gateway_method.dashboard_options.http_method
  status_code = aws_api_gateway_method_response.dashboard_options_200.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}

# POST /agent -> CDSS router Lambda (same auth as /api)
resource "aws_api_gateway_resource" "agent" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "agent"
}

resource "aws_api_gateway_method" "agent_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agent.id
  http_method   = "POST"
  authorization = var.api_require_cognito ? "COGNITO_USER_POOLS" : "NONE"
  authorizer_id = var.api_require_cognito ? aws_api_gateway_authorizer.cognito.id : null
}

resource "aws_api_gateway_integration" "agent" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.agent.id
  http_method             = aws_api_gateway_method.agent_post.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.cdss_lambda.invoke_arn
}

# OPTIONS /agent (CORS preflight)
resource "aws_api_gateway_method" "agent_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agent.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agent_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.agent.id
  http_method = aws_api_gateway_method.agent_options.http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "agent_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.agent.id
  http_method = aws_api_gateway_method.agent_options.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Max-Age"       = true
  }
}

resource "aws_api_gateway_integration_response" "agent_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.agent.id
  http_method = aws_api_gateway_method.agent_options.http_method
  status_code = aws_api_gateway_method_response.agent_options_200.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }
}


# AWS_PROXY passes response through from Lambda; no method/integration response needed

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.health.id,
      aws_api_gateway_resource.api.id,
      aws_api_gateway_resource.api_proxy.id,
      aws_api_gateway_resource.dashboard.id,
      aws_api_gateway_resource.agent.id,
      aws_api_gateway_method.health_get.id,
      aws_api_gateway_integration.health_mock.id,
      aws_api_gateway_method.health_options.id,
      aws_api_gateway_integration.health_options.id,
      aws_api_gateway_method_response.health_options_200.id,
      aws_api_gateway_integration_response.health_options_200.id,
      aws_api_gateway_method.api_proxy_any.id,
      aws_api_gateway_integration.api_proxy.id,
      aws_api_gateway_method.api_proxy_options.id,
      aws_api_gateway_integration.api_proxy_options.id,
      aws_api_gateway_method_response.api_proxy_options_200.id,
      aws_api_gateway_integration_response.api_proxy_options_200.id,
      aws_api_gateway_method.dashboard_get.id,
      aws_api_gateway_integration.dashboard.id,
      aws_api_gateway_method.dashboard_options.id,
      aws_api_gateway_integration.dashboard_options.id,
      aws_api_gateway_method_response.dashboard_options_200.id,
      aws_api_gateway_integration_response.dashboard_options_200.id,
      aws_api_gateway_method.agent_post.id,
      aws_api_gateway_integration.agent.id,
      aws_api_gateway_method.agent_options.id,
      aws_api_gateway_integration.agent_options.id,
      aws_api_gateway_method_response.agent_options_200.id,
      aws_api_gateway_integration_response.agent_options_200.id,
      aws_api_gateway_authorizer.cognito.id,
      aws_api_gateway_gateway_response.default_4xx.id,
      aws_api_gateway_gateway_response.default_5xx.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
}

# -----------------------------------------------------------------------------
# Gateway Responses: add CORS headers to all 4xx/5xx responses from API Gateway.
# When Cognito authorizer returns 401 or a route is missing (403), the response
# is generated by API Gateway, not Lambda, so it would otherwise have no CORS
# headers and the browser blocks with "access control checks".
# -----------------------------------------------------------------------------
locals {
  gateway_response_cors_headers = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "gatewayresponse.header.Access-Control-Max-Age"       = "'86400'"
  }
}

resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_4XX"
  response_parameters = local.gateway_response_cors_headers
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_5XX"
  response_parameters = local.gateway_response_cors_headers
}
