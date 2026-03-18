data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src"
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

resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  count = var.attach_bedrock_policy ? 1 : 0

  role       = aws_iam_role.lambda.name
  policy_arn = var.bedrock_policy_arn
}

# Required for Lambda to create ENIs when running in VPC
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count = length(var.vpc_subnet_ids) > 0 && length(var.vpc_security_group_ids) > 0 ? 1 : 0

  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "this" {
  for_each = var.handlers

  function_name   = "${var.name}-${each.key}-${var.stage}"
  role            = aws_iam_role.lambda.arn
  handler         = each.value
  runtime         = var.runtime
  filename        = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  layers          = var.layers

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 && length(var.vpc_security_group_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  environment {
    variables = merge(var.env, { STAGE = var.stage })
  }

  timeout     = 30
  memory_size = 256
}

output "invoke_arn" {
  value = aws_lambda_function.this["api"].invoke_arn
}

output "worker_function_arn" {
  value = aws_lambda_function.this["agent_worker"].arn
}

output "api_function_name" {
  value = aws_lambda_function.this["api"].function_name
}

output "function_names" {
  value = [for f in aws_lambda_function.this : f.function_name]
}

output "function_names_map" {
  value = { for k, f in aws_lambda_function.this : k => f.function_name }
}

output "function_arns_map" {
  value = { for k, f in aws_lambda_function.this : k => f.arn }
}

output "role_arn" {
  value = aws_iam_role.lambda.arn
}

output "role_name" {
  value = aws_iam_role.lambda.name
}
