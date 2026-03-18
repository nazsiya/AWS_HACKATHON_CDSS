# AC-3: Gateway Lambda → Aurora Connection Debugging

Use this checklist when the Gateway Lambda (cdss-dev-gateway-get-hospitals) returns **synthetic/stub** data instead of live Aurora data, or when you see connection errors in CloudWatch.

---

## 1. CloudWatch logs (first place to look)

In **CloudWatch → Log groups → `/aws/lambda/cdss-dev-gateway-get-hospitals`**, look for:

| Log message | Meaning |
|-------------|---------|
| `[DB] No DATABASE_URL or RDS_CONFIG_SECRET_NAME` | Env var not set; check Lambda config in Terraform / Console. |
| `[DB] Cannot build DB URL from secret: ...` | Secret fetch or token generation failed. See steps 2–4 below. |
| `[DB] Cannot create engine: ...` | SQLAlchemy failed to create engine (e.g. invalid URL). |
| `Hospital DB query failed: ...` or `get_patient DB query failed: ...` | Engine exists but first query failed (network, auth, or schema). |

---

## 2. Lambda environment

- **RDS_CONFIG_SECRET_NAME** must be set (e.g. `cdss-dev/rds-config`).  
  Terraform sets it in `infrastructure/agentcore_gateway.tf` from `aws_secretsmanager_secret.rds_config.name`.
- **AWS_REGION** is set automatically by Lambda; the code defaults to `ap-south-1` if missing.

---

## 3. Secrets Manager secret

- **Secret name** must match `RDS_CONFIG_SECRET_NAME`.
- **Secret value** must be JSON with:
  - `host` – Aurora cluster endpoint (from Terraform: `aws_rds_cluster.aurora.endpoint`).
  - `port` – `5432`.
  - `database` – `cdssdb` (or your DB name).
  - `username` – same as `var.db_username` (master user or IAM user).
  - `region` – optional; Lambda uses `AWS_REGION` for `generate_db_auth_token`.

**No password** is stored; the Lambda uses **IAM database authentication** and calls `rds.generate_db_auth_token()`.

After changing the secret, **redeploy or re-invoke** the Lambda so it picks up the new value (and a new token).

---

## 4. IAM: Lambda role

The Gateway Lambda role must have:

1. **Secrets Manager:** `secretsmanager:GetSecretValue` on the RDS config secret.
2. **RDS IAM auth:** `rds-db:connect` on the resource:
   ```text
   arn:aws:rds-db:<region>:<account>:dbuser:<cluster_resource_id>/<db_username>
   ```
   Terraform sets this in `aws_iam_policy.gateway_tools_services` in `agentcore_gateway.tf`.

If the token step fails, confirm the role has both permissions and that `cluster_resource_id` and `db_username` match the cluster and the user in the secret.

---

## 5. PostgreSQL: IAM role for the DB user

The database user used in the secret must be allowed to use IAM auth:

1. Connect to Aurora as the **master user** (using the master password, e.g. from bastion or temporarily in Secrets Manager).
2. Run:
   ```sql
   GRANT rds_iam TO <db_username>;
   ```
   Use the same `<db_username>` as in the secret (e.g. `cdssadmin` or `var.db_username`).

Without this, Aurora will reject the IAM token and you’ll see connection/auth errors in CloudWatch (e.g. “password authentication failed” or “IAM authentication failed”).

---

## 6. VPC and security groups

- Lambda is in **VPC** with subnets that can reach Aurora (e.g. private subnets with NAT or VPC endpoints for Secrets Manager and RDS API).
- **Lambda security group** must have **egress** to:
  - Aurora **port 5432** (or the cluster’s port).
  - AWS APIs (Secrets Manager, RDS for `generate_db_auth_token`) if using NAT; or use VPC endpoints.
- **Aurora security group** must allow **ingress** on **5432** from the **Lambda security group**.

Terraform: `aws_security_group.aurora` allows `aws_security_group.lambda`; `aws_security_group.lambda` allows all egress.

### If you see `psycopg2.OperationalError` / "connection to server at ..." (timeout)

The Lambda built the URL and created the engine but the **TCP connection to Aurora is failing** (often after ~10 seconds). Check in order:

1. **Same VPC**
   - **Lambda:** Configuration → VPC → note the VPC ID and subnets.
   - **Aurora:** RDS → Clusters → your cluster → Connectivity → VPC and subnets.
   - They must be in the **same VPC**. Aurora’s subnet group should include the same private subnets the Lambda uses (e.g. `private_a`, `private_b`).

2. **Aurora security group inbound**
   - RDS → your cluster → Connectivity → VPC security groups → open the **Aurora** security group.
   - **Inbound rules** must have a rule: **Type** = Custom TCP, **Port** = 5432, **Source** = the **Lambda** security group (e.g. `sg-xxxx` for `cdss-dev-lambda-sg`).
   - If the source is a CIDR or a different SG, add a rule with the Lambda SG as source.

3. **Lambda security group**
   - Lambda → Configuration → VPC → click the Lambda security group.
   - **Outbound** should allow all (0.0.0.0/0) or at least port 5432 to the VPC CIDR (e.g. 10.0.0.0/16).

4. **Aurora status**
   - RDS → Clusters → cluster status must be **Available**.
   - If it is **Starting**, **Modifying**, or **Backing up**, wait until **Available** and try again.

5. **Terraform `enable_lambda_vpc`**
   - In `terraform.tfvars` (or wherever you set it), ensure **`enable_lambda_vpc = true`** so that:
     - Private subnets have a route table (and NAT if Lambda needs internet).
     - VPC endpoints for Secrets Manager (and RDS API if used) exist so the Lambda can get the secret and token.

After changing security groups or route tables, wait a few seconds and invoke the Lambda again. The Lambda code uses a 5-second connect timeout so failures should appear in CloudWatch within about 5 seconds.

---

## 7. Schema: tables exist

The Lambda runs SQL against:

- `hospitals` (for `get_hospitals`)
- `patients`, `visits` (for `get_patient`, `list_patients`)
- `surgeries`, `resources`, `schedule_slots`, `medications`, `reminders` (for other tools)

If the **first query** fails with “relation … does not exist”, run migrations or seed so these tables exist in `cdssdb`. See project docs for RDS schema and seed scripts.

---

## 8. Quick verification

1. **Invoke the Lambda** from the AWS Console (Test tab) with a test event, e.g.:
   ```json
   { "tool_name": "get_patient", "patient_id": "PT-1001" }
   ```
   (If the Gateway passes tool name via context, use an event that your Gateway sends for that tool.)

2. Check the **response**:
   - `"source": "database"` → Aurora connection and query succeeded.
   - `"source": "synthetic"` or `"error": "Database not available"` → connection or config issue; use CloudWatch and this checklist.

3. **CloudWatch**: Open the log stream for that invocation and look for `[DB]` messages to see which step failed.

---

## Summary checklist

- [ ] Lambda env: `RDS_CONFIG_SECRET_NAME` set.
- [ ] Secret: JSON with `host`, `port`, `database`, `username` (no password).
- [ ] Lambda IAM: Secrets Manager + `rds-db:connect` for `dbuser:<cluster_resource_id>/<username>`.
- [ ] PostgreSQL: `GRANT rds_iam TO <db_username>;` for the user in the secret.
- [ ] VPC: Lambda can reach Aurora (5432) and AWS APIs (Secrets Manager, RDS).
- [ ] Aurora SG: allows Lambda SG on 5432.
- [ ] Schema: required tables exist in `cdssdb`.

After fixing, redeploy the Lambda (e.g. `terraform apply` or update code/config in Console) and trigger a tool again; check response and CloudWatch logs.
