# Deploy and test CDSS infrastructure

## Is the infrastructure deployed?

**No.** There is no `terraform.tfstate` with successfully applied resources. A previous `terraform apply` failed because the AWS IAM user used does not have enough permissions.

## What you need to deploy

1. **AWS credentials** with permissions to create and tag:
   - **API Gateway**: CreateRestApi, PUT (including tags)
   - **Lambda**: CreateFunction, CreateRole, etc.
   - **IAM**: CreateRole, CreatePolicy, **TagRole**, **TagPolicy**
   - **S3**: CreateBucket, GetBucketPolicy, PutBucketVersioning, etc.
   - **DynamoDB**: CreateTable
   - **EventBridge**: CreateEventBus, **TagResource**
   - **Secrets Manager**: CreateSecret
   - **EC2/VPC**: CreateVpc, CreateSubnet, CreateSecurityGroup, etc. (and **DescribeImages** if using bastion)
   - **Bedrock**: no resource creation; IAM policy is created for Lambda to invoke Bedrock

2. **terraform.tfvars** in `infrastructure/` with at least:
   - `db_username` = master username for RDS
   - `db_password` = master password for RDS

3. **Deploy** (from `infrastructure/`):
   ```powershell
   terraform init -reconfigure
   terraform plan -out=tfplan
   terraform apply tfplan
   ```
   Or: `terraform apply -auto-approve`

## After a successful deploy: test the API

From the repo root or from `infrastructure/`:

```powershell
.\infrastructure\test-api.ps1
```

Or manually:

```powershell
cd infrastructure
$url = terraform output -raw api_gateway_url
Invoke-WebRequest -Uri "$url/health" -Method GET
Invoke-WebRequest -Uri "$url/api/" -Method GET
```

You should see:
- **GET /health** → `{"status":"ok","service":"cdss"}`
- **GET /api/** → `{"service":"cdss","status":"ok"}`

## If your IAM user cannot be granted tagging permissions

Some errors are due to **default_tags** in the provider (Project, ManagedBy) and AWS applying them to resources that support tags. If your org does not allow `iam:TagRole`, `apigateway:PUT` (tags), etc., you can try removing `default_tags` from `provider.tf` and re-running apply. Other permissions (CreateVpc, CreateTable, CreateSecret, etc.) are still required.
