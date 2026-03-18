data "archive_file" "health_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda_health.js"
  output_path = "${path.module}/lambda_health.zip"
}

resource "aws_iam_role" "health_lambda" {
  name = "${local.name_prefix}-health-lambda-role"

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

resource "aws_iam_role_policy_attachment" "health_lambda" {
  role       = aws_iam_role.health_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "health" {
  filename         = data.archive_file.health_lambda.output_path
  function_name    = "${local.name_prefix}-health"
  role             = aws_iam_role.health_lambda.arn
  handler          = "lambda_health.handler"
  source_code_hash = data.archive_file.health_lambda.output_base64sha256
  runtime          = "nodejs20.x"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
