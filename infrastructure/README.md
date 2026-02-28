# CDSS Infrastructure (Terraform)

This folder contains everything needed to deploy the CDSS backend on AWS.

---

## 1. Terraform configuration files

| File | Purpose |
|------|--------|
| **main.tf** | Root configuration: Terraform & provider blocks, Lambda, API Gateway, DynamoDB, S3, EventBridge modules |
| **variables.tf** | Variable definitions: `aws_region`, `stage`, `lambda_handlers`, `lambda_env` |
| **outputs.tf** | Outputs: API Gateway URL, Lambda names, DynamoDB tables, S3 buckets |
| **backend.tf** | Backend configuration (S3 remote state — uncomment and set bucket/key) |
| **modules/** | Reusable modules: `lambda`, `api_gateway`, `dynamodb`, `s3`, `eventbridge` |

---

## 2. Variables definition

- **Root** (`variables.tf`): `aws_region` (default `ap-south-1`), `stage` (dev/prod), `lambda_handlers`, `lambda_env`.
- **Per-module** (`modules/*/variables.tf`): `name`, `stage`, and module-specific inputs (e.g. `lambda_invoke_arn` for API Gateway).

Override at deploy time:

```powershell
terraform plan -var "stage=prod" -var "aws_region=ap-south-1"
```

---

## 3. Deploy infrastructure with Terraform

**Prerequisites:** Terraform installed, AWS CLI configured (e.g. `aws configure`), credentials for `ap-south-1`.

**Option A — Manual commands**

```powershell
cd d:\CDSS\infrastructure
terraform init
terraform plan -var stage=dev
terraform apply -var stage=dev
```

**Option B — Use the deploy script**

```powershell
cd d:\CDSS\infrastructure
.\deploy.ps1 -Stage dev
```

**After deploy**

- Get API URL: `terraform output api_gateway_url`
- Optional: configure remote backend in `backend.tf` (S3 bucket + DynamoDB lock table) for team use.

See project root [docs/deployment.md](../docs/deployment.md) for full deployment and Lambda env details.
