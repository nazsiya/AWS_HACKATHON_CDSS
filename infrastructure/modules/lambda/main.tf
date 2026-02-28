data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_iam_role" "lambda" {
  name = "${var.name}-lambda-${var.stage}"

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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "this" {
  for_each = var.handlers

  function_name = "${var.name}-${each.key}-${var.stage}"
  role          = aws_iam_role.lambda.arn
  handler       = each.value
  runtime       = var.runtime
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = merge(var.env, { STAGE = var.stage })
  }

  timeout     = 30
  memory_size = 256
}

# API Gateway invokes the router Lambda (api)
output "invoke_arn" {
  value = aws_lambda_function.this["api"].invoke_arn
}

output "function_names" {
  value = [for f in aws_lambda_function.this : f.function_name]
}
