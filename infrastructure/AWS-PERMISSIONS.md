# AWS permissions required for CDSS infrastructure

To run `terraform apply` successfully, the IAM user or role you use (e.g. Nazim) must have permissions for the services and actions below. You can either attach **AWS managed policies** (simplest) or one **custom policy** (minimal).

---

## Option A: AWS managed policies (attach these to your IAM user/role)

Attach the following **managed policies** to the IAM user or role that runs Terraform. These are the standard AWS names; your admin can find them in IAM → Policies → AWS managed.

| # | Policy name | Used for |
|---|-------------|----------|
| 1 | **AmazonAPIGatewayAdministrator** | API Gateway REST API, resources, methods, integrations, deployment, stage |
| 2 | **AWSLambda_FullAccess** | Lambda functions, permissions (invoke from API Gateway) |
| 3 | **IAMFullAccess** | CreateRole, CreatePolicy, AttachRolePolicy, TagRole, TagPolicy, PassRole (needed for Lambda execution roles and Bedrock policy) |
| 4 | **AmazonS3FullAccess** | S3 buckets (main, documents, corpus), versioning, encryption, public access block. Must include **s3:GetBucketPolicy** (Terraform reads it during refresh). |
| 5 | **AmazonDynamoDBFullAccess** | DynamoDB tables (sessions, medication_schedules, patients, consultations, ot_slots, equipment, protocols) |
| 6 | **CloudWatchEventsFullAccess** | EventBridge event bus |
| 7 | **SecretsManagerReadWrite** | Secrets Manager secrets and versions (bedrock-config, rds-config) |
| 8 | **AmazonRDSFullAccess** | RDS Aurora cluster and instance |
| 9 | **AmazonVPCFullAccess** | VPC, subnets, security groups, route tables, internet gateway, subnet groups |

**If you use the bastion host** (`enable_bastion = true` in tfvars):

| 10 | **AmazonEC2FullAccess** | EC2 instance (bastion), key pair, DescribeImages (AMI lookup) |

**Total: 9 policies without bastion, 10 with bastion.**

---

## Option B: One custom policy (minimal, single policy)

If your admin prefers a single custom policy instead of 10 managed ones, create an IAM policy with the JSON below. This scopes permissions to the actions Terraform actually uses (and includes tagging so `default_tags` works). Replace `ACCOUNT_ID` with your AWS account ID (e.g. `746412758276`) and optionally restrict `Resource` to specific ARN patterns for your project.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "APIGateway",
      "Effect": "Allow",
      "Action": [
        "apigateway:*"
      ],
      "Resource": "arn:aws:apigateway:*::/*"
    },
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": [
        "lambda:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRolesPolicies",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:GetPolicy",
        "iam:TagPolicy",
        "iam:UntagPolicy",
        "iam:CreatePolicyVersion",
        "iam:DeletePolicyVersion",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListRolePolicies"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EventBridge",
      "Effect": "Allow",
      "Action": [
        "events:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManager",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RDS",
      "Effect": "Allow",
      "Action": [
        "rds:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPC",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc",
        "ec2:DeleteVpc",
        "ec2:DescribeVpcs",
        "ec2:CreateSubnet",
        "ec2:DeleteSubnet",
        "ec2:DescribeSubnets",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:CreateInternetGateway",
        "ec2:DeleteInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:DetachInternetGateway",
        "ec2:DescribeInternetGateways",
        "ec2:CreateRouteTable",
        "ec2:DeleteRouteTable",
        "ec2:DescribeRouteTables",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:AssociateRouteTable",
        "ec2:DisassociateRouteTable",
        "ec2:CreateDbSubnetGroup",
        "ec2:DeleteDbSubnetGroup",
        "ec2:DescribeDbSubnetGroups"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2Bastion",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeImages",
        "ec2:CreateKeyPair",
        "ec2:DeleteKeyPair",
        "ec2:DescribeKeyPairs"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** Option B still grants broad permissions per service (e.g. `lambda:*`, `s3:*`). For stricter least-privilege, your admin can restrict `Resource` to ARNs like `arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:cdss-*` and similar for other services.

---

## Do you need all of them?

**Yes, for a full deploy.** Each service is used by the Terraform config:

| Service | Used for |
|---------|----------|
| API Gateway | REST API with `/health`, `/api/v1/*` (CDSS; includes `/api/v1/triage` for severity assessment) |
| Lambda | Health Lambda, CDSS router + agent Lambdas |
| IAM | Execution roles for Lambdas, Bedrock invoke policy |
| S3 | Main bucket, documents bucket, corpus bucket |
| DynamoDB | Sessions, medication_schedules, patients, consultations, ot_slots, equipment, protocols |
| EventBridge | CDSS event bus for async messaging |
| Secrets Manager | Bedrock config, RDS config |
| RDS | Aurora PostgreSQL (cdssdb) |
| VPC | Network for RDS and (optionally) Lambda/bastion |
| EC2 (bastion only) | Bastion host for SSH tunnel to RDS when `enable_bastion = true` |

**If you want to skip RDS (e.g. use an existing DB):** You would need to change the Terraform to make RDS optional (variable + count). Out of the box, RDS is required.

**If you disable the bastion** (`enable_bastion = false`, default): You do **not** need **AmazonEC2FullAccess**; **AmazonVPCFullAccess** is enough for VPC/subnets/security groups.

---

## Summary for your admin

- **Simplest:** Attach the **9 managed policies** in the table (Option A). Add **AmazonEC2FullAccess** only if bastion is enabled.
- **Single policy:** Create one custom policy with the JSON above (Option B) and attach it to the Terraform user/role.
- **Policy names (exact):**  
  `AmazonAPIGatewayAdministrator`, `AWSLambda_FullAccess`, `IAMFullAccess`, `AmazonS3FullAccess`, `AmazonDynamoDBFullAccess`, `CloudWatchEventsFullAccess`, `SecretsManagerReadWrite`, `AmazonRDSFullAccess`, `AmazonVPCFullAccess`, and (optional) `AmazonEC2FullAccess`.
