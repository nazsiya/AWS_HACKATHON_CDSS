resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  alias_attributes         = ["preferred_username", "email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    name                     = "role"
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = {
    Name    = "${local.name_prefix}-user-pool"
    Project = var.project_name
  }
}

resource "aws_cognito_user_pool_client" "staff_app" {
  name         = "${local.name_prefix}-staff-app-client"
  user_pool_id = aws_cognito_user_pool.main.id

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  callback_urls = compact([
    "http://localhost:3000/",
    "http://localhost:3001/",
    var.staff_app_domain != "" ? "https://${var.staff_app_domain}/" : "",
    var.patient_portal_domain != "" ? "https://${var.patient_portal_domain}/" : "",
  ])

  logout_urls = compact([
    "http://localhost:3000/",
    "http://localhost:3001/",
    var.staff_app_domain != "" ? "https://${var.staff_app_domain}/" : "",
    var.patient_portal_domain != "" ? "https://${var.patient_portal_domain}/" : "",
  ])

  prevent_user_existence_errors = "ENABLED"
}

resource "aws_cognito_user_pool_client" "patient_portal" {
  name         = "${local.name_prefix}-patient-portal-client"
  user_pool_id = aws_cognito_user_pool.main.id

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  callback_urls = compact([
    "http://localhost:3000/",
    "http://localhost:3001/",
    var.staff_app_domain != "" ? "https://${var.staff_app_domain}/" : "",
    var.patient_portal_domain != "" ? "https://${var.patient_portal_domain}/" : "",
  ])

  logout_urls = compact([
    "http://localhost:3000/",
    "http://localhost:3001/",
    var.staff_app_domain != "" ? "https://${var.staff_app_domain}/" : "",
    var.patient_portal_domain != "" ? "https://${var.patient_portal_domain}/" : "",
  ])

  prevent_user_existence_errors = "ENABLED"
}

# API Gateway Authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name          = "${local.name_prefix}-cognito-authorizer"
  rest_api_id   = aws_api_gateway_rest_api.main.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [aws_cognito_user_pool.main.arn]
}
