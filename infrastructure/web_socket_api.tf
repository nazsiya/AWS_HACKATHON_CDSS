# WebSocket API for real-time surgical updates (Phase 4)
# Package Python handler from backend/api/websocket
data "archive_file" "websocket_lambda" {
  count       = var.enable_websocket_api ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../backend/api/websocket"
  output_path = "${path.module}/websocket_lambda.zip"
}

# Build WebSocket $connect authorizer Lambda zip (includes PyJWT/cryptography)
resource "null_resource" "websocket_authorizer_build" {
  count = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0

  triggers = {
    authorizer_py = filemd5("${path.module}/../backend/api/websocket_authorizer/authorizer.py")
    requirements   = filemd5("${path.module}/../backend/api/websocket_authorizer/requirements.txt")
  }

  provisioner "local-exec" {
    command     = "python scripts/build_websocket_authorizer.py"
    working_dir = "${path.module}/.."
  }
}

resource "aws_apigatewayv2_api" "websocket" {
  count = var.enable_websocket_api ? 1 : 0

  name                       = "${local.name_prefix}-websocket-api"
  protocol_type               = "WEBSOCKET"
  route_selection_expression = "$request.body.action"

  tags = {
    Name    = "${local.name_prefix}-websocket-api"
    Project = var.project_name
  }
}

resource "aws_apigatewayv2_stage" "websocket" {
  count = var.enable_websocket_api ? 1 : 0

  api_id      = aws_apigatewayv2_api.websocket[0].id
  name        = var.environment
  auto_deploy = true
}

# Simple handler for WebSocket connections (placeholder)
resource "aws_iam_role" "websocket_lambda" {
  count = var.enable_websocket_api ? 1 : 0
  name  = "${local.name_prefix}-websocket-role"

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

resource "aws_iam_role_policy_attachment" "websocket_lambda" {
  count      = var.enable_websocket_api ? 1 : 0
  role       = aws_iam_role.websocket_lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "websocket_lambda_apigw" {
  count = var.enable_websocket_api ? 1 : 0

  name   = "${local.name_prefix}-websocket-apigw-manage-connections"
  role   = aws_iam_role.websocket_lambda[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "execute-api:ManageConnections"
        Resource = "${aws_apigatewayv2_stage.websocket[0].execution_arn}/POST/@connections/*"
      }
    ]
  })
}

resource "aws_lambda_function" "websocket_handler" {
  count = var.enable_websocket_api ? 1 : 0

  function_name    = "${local.name_prefix}-websocket-handler"
  role             = aws_iam_role.websocket_lambda[0].arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.websocket_lambda[0].output_path
  source_code_hash = data.archive_file.websocket_lambda[0].output_base64sha256
}

# --- WebSocket $connect JWT authorizer (Cognito) ---
resource "aws_iam_role" "websocket_authorizer" {
  count = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0

  name = "${local.name_prefix}-websocket-authorizer-role"

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

resource "aws_iam_role_policy_attachment" "websocket_authorizer" {
  count      = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0
  role       = aws_iam_role.websocket_authorizer[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "websocket_authorizer" {
  count = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0

  function_name    = "${local.name_prefix}-websocket-authorizer"
  role             = aws_iam_role.websocket_authorizer[0].arn
  handler          = "authorizer.lambda_handler"
  runtime          = "python3.12"
  filename         = "${path.module}/websocket_authorizer_lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/websocket_authorizer_lambda.zip")

  environment {
    variables = {
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      # AWS_REGION is reserved; Lambda receives it automatically
    }
  }

  depends_on = [null_resource.websocket_authorizer_build]
}

resource "aws_apigatewayv2_authorizer" "ws_connect" {
  count = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0

  api_id           = aws_apigatewayv2_api.websocket[0].id
  authorizer_type  = "REQUEST"
  authorizer_uri   = aws_lambda_function.websocket_authorizer[0].invoke_arn
  identity_sources = ["route.request.querystring.token"]
  name             = "${local.name_prefix}-ws-connect-authorizer"
}

resource "aws_lambda_permission" "websocket_authorizer" {
  count = var.enable_websocket_api && var.enable_websocket_authorizer ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke-${aws_apigatewayv2_api.websocket[0].id}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_authorizer[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket[0].execution_arn}/authorizers/${aws_apigatewayv2_authorizer.ws_connect[0].id}"
}

# Routes
resource "aws_apigatewayv2_route" "connect" {
  count = var.enable_websocket_api ? 1 : 0

  api_id    = aws_apigatewayv2_api.websocket[0].id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket[0].id}"

  authorization_type = var.enable_websocket_authorizer ? "CUSTOM" : "NONE"
  authorizer_id       = var.enable_websocket_authorizer ? aws_apigatewayv2_authorizer.ws_connect[0].id : null
}

resource "aws_apigatewayv2_route" "disconnect" {
  count = var.enable_websocket_api ? 1 : 0

  api_id    = aws_apigatewayv2_api.websocket[0].id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket[0].id}"
}

resource "aws_apigatewayv2_route" "default" {
  count = var.enable_websocket_api ? 1 : 0

  api_id    = aws_apigatewayv2_api.websocket[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.websocket[0].id}"
}

resource "aws_apigatewayv2_integration" "websocket" {
  count = var.enable_websocket_api ? 1 : 0

  api_id           = aws_apigatewayv2_api.websocket[0].id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.websocket_handler[0].invoke_arn
}

resource "aws_lambda_permission" "websocket_api_gateway" {
  count = var.enable_websocket_api ? 1 : 0

  statement_id  = "AllowExecutionFromApiGateway-${aws_apigatewayv2_api.websocket[0].id}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.websocket_handler[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket[0].execution_arn}/*/*"
}
