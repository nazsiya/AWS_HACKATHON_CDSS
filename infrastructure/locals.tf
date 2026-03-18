locals {
  name_prefix = "${var.project_name}-${var.environment}"
  stage       = var.environment
}
