# Deployment

## Prerequisites

- Python 3.12
- Terraform >= 1.5
- AWS CLI configured (ap-south-1)
- Bedrock model access (Claude 3 Haiku) in your account

## Backend (Terraform)

1. Configure remote backend in `infrastructure/backend.tf` (S3 bucket + optional DynamoDB lock).
2. From `infrastructure/`:

   ```bash
   terraform init
   terraform plan -var stage=dev
   terraform apply -var stage=dev
   ```

3. Package Lambda from repo root: Terraform uses `source_dir = "../../src"`; ensure `src/cdss` and dependencies are present. Run `pip install -r requirements.txt -t src/` if you bundle deps into the zip, or use Lambda layers.

## Environment Variables (Lambda)

Set via Terraform `lambda_env` or Secrets Manager:

- `AWS_REGION`: ap-south-1
- `STAGE`: dev | prod
- `BEDROCK_MODEL_ID`: anthropic.claude-3-haiku-20240307-v1:0
- `OPENSEARCH_ENDPOINT`: (optional) RAG
- `DYNAMODB_SESSIONS_TABLE`, `DYNAMODB_MEDICATION_TABLE`
- `S3_BUCKET_DOCUMENTS`, `S3_BUCKET_CORPUS`
- `EVENT_BUS_NAME`, `PINPOINT_APP_ID`, `DISHA_AUDIT_LOG_GROUP`

## Frontend (Amplify)

Deploy React app via AWS Amplify; point API to the API Gateway URL from `terraform output api_gateway_url`.
