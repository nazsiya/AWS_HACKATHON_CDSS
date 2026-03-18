# CDSS AWS Provisioned Resources and Region

## Where the region is set

| Location | What | Current value |
|----------|------|----------------|
| **infrastructure/terraform.tfvars** | `aws_region` | **ap-south-1** |
| **infrastructure/variables.tf** | `variable "aws_region"` default | us-east-1 (overridden by tfvars) |
| **infrastructure/provider.tf** | `provider "aws" { region = var.aws_region }` | Uses tfvars → **ap-south-1** |

**All resources below are provisioned in the same region:** the one set in `terraform.tfvars` (currently **ap-south-1**). There is no per-resource region; the single AWS provider region applies to every resource.

---

## Provisioned resources (by Terraform)

Everything is defined under **infrastructure/** and created in **ap-south-1** when you run `terraform apply` with the current tfvars.

### Compute & API

| Resource | Terraform address | File |
|----------|-------------------|------|
| REST API Gateway | `aws_api_gateway_rest_api.main` | api_gateway.tf |
| API resources: /health, /api/{proxy+}, /dashboard, /agent | `aws_api_gateway_resource.*`, `aws_api_gateway_method.*`, `aws_api_gateway_integration.*` | api_gateway.tf |
| API deployment & stage | `aws_api_gateway_deployment.main`, `aws_api_gateway_stage.main` | api_gateway.tf |
| Health Lambda | `aws_lambda_function.health` | lambda.tf |
| CDSS Lambdas (api, supervisor, patient, surgery, resource, scheduling, engagement) | `module.cdss_lambda.aws_lambda_function.this` | modules/lambda/main.tf |
| WebSocket API (optional) | `aws_apigatewayv2_api.websocket`, stage, routes, websocket Lambda | web_socket_api.tf |

### Database

| Resource | Terraform address | File |
|----------|-------------------|------|
| Aurora PostgreSQL cluster | `aws_rds_cluster.aurora` | rds.tf |
| Aurora instance | `aws_rds_cluster_instance.aurora` | rds.tf |
| DB subnet group | `aws_db_subnet_group.aurora` | vpc.tf |
| Aurora security group | `aws_security_group.aurora` | vpc.tf |

### Storage (S3)

| Resource | Terraform address | File |
|----------|-------------------|------|
| Main bucket | `aws_s3_bucket.main` (+ versioning, encryption, public block) | s3.tf |
| Documents bucket | `aws_s3_bucket.documents` (+ versioning, encryption, public block) | s3.tf |
| Corpus bucket | `aws_s3_bucket.corpus` (+ encryption, public block) | s3.tf |
| Bucket policies (CloudFront OAC) | `aws_s3_bucket_policy.staff_bucket_access`, `patient_bucket_access` | frontend.tf |

### Secrets & config

| Resource | Terraform address | File |
|----------|-------------------|------|
| Bedrock config secret | `aws_secretsmanager_secret.bedrock_config` + version | secrets.tf |
| RDS config secret | `aws_secretsmanager_secret.rds_config` + version | secrets.tf |
| SSM: transcriptions_enabled | `aws_ssm_parameter.transcriptions_enabled` | parameter_store.tf |
| SSM: translation_enabled | `aws_ssm_parameter.translation_enabled` | parameter_store.tf |
| SSM: abdm_integration_enabled | `aws_ssm_parameter.abdm_integration_enabled` | parameter_store.tf |

### Messaging & events

| Resource | Terraform address | File |
|----------|-------------------|------|
| EventBridge bus | `module.cdss_eventbridge.aws_cloudwatch_event_bus.cdss` | modules/eventbridge/main.tf |
| SQS agent_events | `aws_sqs_queue.agent_events` | notifications.tf |
| SQS agent_events DLQ | `aws_sqs_queue.agent_events_dlq` | notifications.tf |
| SQS redrive policy | `aws_sqs_queue_redrive_policy.agent_events` | notifications.tf |
| EventBridge rule → SQS | `aws_cloudwatch_event_rule.inter_agent_messaging`, `aws_cloudwatch_event_target.sqs` | notifications.tf |
| SQS policy (EventBridge) | `aws_sqs_queue_policy.agent_events` | notifications.tf |
| SNS patient_reminders | `aws_sns_topic.patient_reminders` | notifications.tf |
| SNS doctor_escalations | `aws_sns_topic.doctor_escalations` | notifications.tf |

### Auth

| Resource | Terraform address | File |
|----------|-------------------|------|
| Cognito user pool | `aws_cognito_user_pool.main` | auth.tf |
| Cognito clients (staff, patient) | `aws_cognito_user_pool_client.staff_app`, `patient_portal` | auth.tf |
| API Gateway authorizer | `aws_api_gateway_authorizer.cognito` | auth.tf |

### Frontend / CDN

| Resource | Terraform address | File |
|----------|-------------------|------|
| CloudFront OAC | `aws_cloudfront_origin_access_control.main` | frontend.tf |
| CloudFront staff app | `aws_cloudfront_distribution.staff_app` | frontend.tf |
| CloudFront patient portal | `aws_cloudfront_distribution.patient_portal` | frontend.tf |

### Networking (VPC)

| Resource | Terraform address | File |
|----------|-------------------|------|
| VPC | `aws_vpc.main` | vpc.tf |
| Private subnets (a, b) | `aws_subnet.private_a`, `aws_subnet.private_b` | vpc.tf |
| Lambda security group | `aws_security_group.lambda` | vpc.tf |

### IAM

| Resource | Terraform address | File |
|----------|-------------------|------|
| Bedrock invoke policy | `aws_iam_policy.bedrock_invoke` | bedrock.tf |
| CDSS Lambda services policy | `aws_iam_policy.cdss_lambda_services` | lambda_iam.tf |
| Health Lambda role | `aws_iam_role.health_lambda` + attachment | lambda.tf |
| CDSS Lambda role | `module.cdss_lambda.aws_iam_role.lambda` + attachments | modules/lambda/main.tf |
| CDSS Lambda services attachment | `aws_iam_role_policy_attachment.cdss_lambda_services` | main.tf |
| WebSocket Lambda role | `aws_iam_role.websocket_lambda` + attachment | web_socket_api.tf |

### Lambda permissions (API Gateway invoke)

| Resource | Terraform address | File |
|----------|-------------------|------|
| /api/* | `aws_lambda_permission.cdss_api_gateway` | api_gateway.tf |
| GET /dashboard | `aws_lambda_permission.cdss_api_gateway_dashboard` | api_gateway.tf |
| POST /agent | `aws_lambda_permission.cdss_api_gateway_agent` | api_gateway.tf |
| Health | `aws_lambda_permission.api_gateway` | lambda.tf |
| WebSocket | `aws_lambda_permission.websocket_api_gateway` | web_socket_api.tf |

---

## Summary

- **Region:** All of the above are in **ap-south-1** (set in **infrastructure/terraform.tfvars** as `aws_region = "ap-south-1"`).
- **Definition:** Every resource is under **infrastructure/** in the `.tf` files listed above.
- **Outputs:** Run `terraform output` in **infrastructure/** to see endpoints, URLs, and secret names (e.g. `aurora_cluster_endpoint`, `api_gateway_url`, `rds_config_secret_name`).

To change the region for new applies (and new resources), change `aws_region` in **terraform.tfvars** and see **docs/region-change-options.md** if you need to keep existing resources in the current region.
