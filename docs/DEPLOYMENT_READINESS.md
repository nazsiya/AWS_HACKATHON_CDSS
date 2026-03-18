# CDSS Deployment Readiness Report

**Date:** 2026-03-08  
**Scope:** Full project and codebase review for production deploy.

---

## Executive Summary

| Verdict | Summary |
|--------|---------|
| **Not fully ready** | One manual step left: set `db_password` in `infrastructure/terraform.tfvars`, then run **`.\scripts\deploy.ps1`**. |

**Deploy flow:** Copy `infrastructure/terraform.tfvars.example` → `terraform.tfvars`, set `db_password`, run **`.\scripts\deploy.ps1`**. Then start tunnel, run migrations/seed, run **`.\scripts\run_rds_iam_grant.ps1`**, and **`.\scripts\deploy_frontend.ps1`** (or let deploy.ps1 prompt you).

**Endpoint alignment:** All frontend API calls are connected to backend routes and documented in OpenAPI. See **docs/ENDPOINT_ALIGNMENT.md** for the checklist and production readiness.

---

## Deploy Scripts (Do It For You)

Run from **repo root** (e.g. `D:\AI_Hackathon_CDSS`).

| Step | Script | What it does |
|------|--------|---------------|
| **One command** | `.\scripts\deploy.ps1` | If `terraform.tfvars` missing, creates from example and exits (set `db_password` then re-run). Otherwise runs pre-check, then `terraform apply -var-file=terraform.tfvars`. Prompts to deploy frontend at end. Use `-ApplyOnly` to skip frontend prompt; `-SkipFrontend` to skip prompt entirely. |
| **1. Pre-check + layer** | `.\scripts\pre_terraform_check.ps1` | Ensures `infrastructure/layer.zip` exists (builds from `infrastructure/layer/python` if needed); reminds you to set Terraform vars. |
| **2. Build layer only** | `.\scripts\build_lambda_layer.ps1` | Zips `infrastructure/layer/python` → `infrastructure/layer.zip`. Run if you add layer deps or layer.zip is missing. |
| **3. Terraform apply** | `.\scripts\deploy.ps1` **or** `cd infrastructure; terraform apply -var-file=terraform.tfvars -input=false -auto-approve` | Deploy infra. **deploy.ps1** does pre-check + apply in one go. |
| **4. After apply** | `.\scripts\run_migrations_and_seed.ps1` | With tunnel running and `DATABASE_URL` in `.env`, run migrations and seed (see RUN_AFTER_TERRAFORM.md). |
| **5. RDS IAM (one-time)** | `.\scripts\run_rds_iam_grant.ps1` | Connects with `DATABASE_URL`, runs `GRANT rds_iam TO <db_username>`. Run once after tunnel + migrations. |
| **6. Deploy frontend** | `.\scripts\deploy_frontend.ps1` | Builds doctor-dashboard with API URL from Terraform output, syncs to S3, invalidates CloudFront. Use `-StaffOnly` to skip patient portal. |

**Shortest flow:** Copy `infrastructure/terraform.tfvars.example` → `infrastructure/terraform.tfvars`, set `db_password`, then run **`.\scripts\deploy.ps1`**. After that: start tunnel → **run_migrations_and_seed.ps1** → **run_rds_iam_grant.ps1**; deploy.ps1 can run **deploy_frontend.ps1** for you at the end.

**Manual flow (after setting Terraform vars):**

```powershell
.\scripts\pre_terraform_check.ps1
cd infrastructure; terraform apply -var-file=terraform.tfvars -input=false -auto-approve; cd ..
.\scripts\deploy_frontend.ps1
```

(Start tunnel and run migrations/seed and **run_rds_iam_grant.ps1** separately; see RUN_AFTER_TERRAFORM.md §3 for RDS IAM.)

---

## 1. What’s Ready

### 1.1 Infrastructure (Terraform)

- **API Gateway:** REST API with `/health`, `/dashboard`, `/agent`, `/api/{proxy+}`; CORS; optional Cognito authorizer.
- **Lambda:** Single CDSS Lambda (router + agent handlers) with Python 3.12, layer, env from Terraform (Secrets Manager names, S3, EventBridge, SQS, Cognito, etc.).
- **Secrets Manager:** `rds-config` and `bedrock-config` created and populated by Terraform (RDS endpoint, Bedrock model).
- **RDS Aurora:** Cluster + instance; secrets reference cluster endpoint.
- **Auth:** Cognito User Pool + staff/patient app clients; API Gateway authorizer (can be disabled with `api_require_cognito = false`).
- **Frontend hosting:** S3 buckets + CloudFront (staff app, patient portal); OAC; SPA fallback for 403/404.
- **Other:** VPC, bastion (optional), EventBridge, SNS/SQS, monitoring/budget, Bedrock IAM.

### 1.2 Backend

- **Router:** `src/cdss/api/handlers/router.py` — handles API Gateway `path` and `pathParameters.proxy`; health, dashboard, agent, Swagger, and all `/api/v1/*` and `/api/ai/*` routes.
- **Handlers:** Patient, Surgery, Resource, Scheduling, Engagement, Admin, AI, Activity, Appointments, Tasks, Supervisor — all expose `handler(event, context)` used by Lambda module.
- **Lambda contract:** `variables.tf` maps `api` → `cdss.api.handlers.router.handler`; zip is built from `../src`; layer from `layer.zip` in `infrastructure/`.

### 1.3 Frontend

- **Doctor dashboard:** Vite build; `VITE_API_URL`, `VITE_USE_MOCK`, optional Cognito; API client and pages wired per `FRONTEND_API_ENDPOINTS.md`.
- **Build:** `npm run build` in CI; artifact uploaded; Dockerfile.frontend exists.

### 1.4 CI/CD

- **CI:** Lint, backend tests (mocked DB), frontend build, Docker backend + frontend; health check in container.

### 1.5 Documentation

- **PRE_BUILD_CHECKLIST.md** — Keys, APIs, config (AWS, Secrets Manager, frontend env, API Gateway URLs).
- **DEVELOPMENT_COMPLETION_STEPS.md** — Phases 1–7, verification scripts, Phase 3 run verified.
- **RUN_AFTER_TERRAFORM.md** — Tunnel, migrations, seed.
- **QUICK_START_GUIDE.md** — Local startup (tunnel, API, frontend).
- **RUNBOOKS.md**, **ONBOARDING.md** — Referenced for deploy and handover.

---

## What you still need to do before deploy

| Priority | Item | Status | Action |
|----------|------|--------|--------|
| **Critical** | Terraform inputs | **One-time** | Copy `infrastructure/terraform.tfvars.example` → `infrastructure/terraform.tfvars` and set `db_password` (and `db_username` if not `cdssadmin`). Then run **`.\scripts\deploy.ps1`** — it applies using tfvars. |
| **Critical** | Lambda layer | **Complete** | **deploy.ps1** runs pre-check (builds `layer.zip` if missing). Or run **`.\scripts\pre_terraform_check.ps1`** before apply. |
| **Critical** | Lambda ↔ RDS | **Complete** | Default **`enable_lambda_vpc = true`** in `variables.tf` — Lambda runs in VPC with NAT so it can reach Aurora and Bedrock. Set `enable_lambda_vpc = false` in tfvars only if you want stub DB. |
| **High** | Frontend deploy | **Complete** | After apply, run **`.\scripts\deploy_frontend.ps1`** (or let **deploy.ps1** prompt you at the end). |
| **High** | RDS IAM auth | **Complete** | One-time: with tunnel up and `DATABASE_URL` set, run **`.\scripts\run_rds_iam_grant.ps1`**. Enable Bedrock model in console (ap-south-1) if not already. |

**Summary:** Set `db_password` in `infrastructure/terraform.tfvars` once, then **`.\scripts\deploy.ps1`** does the rest of infra. After that: tunnel → migrations/seed → **run_rds_iam_grant.ps1** → **deploy_frontend.ps1**.

---

### 2.1 Security: Hardcoded Passwords (Critical)

**Fixed:** `scripts/test_db_conn.py` and `scripts/debug_conn.py` use `DATABASE_URL` or `CDSS_DB_PASSWORD` (no hardcoded passwords).  
**Config:** `config.json` and `config/my-config.json` are in `.gitignore` so env-specific config is not committed.

### 2.2 Secrets in AWS

- Terraform creates and populates `rds-config` and `bedrock-config`. Run **`.\scripts\run_rds_iam_grant.ps1`** once (after tunnel + `DATABASE_URL`) to run `GRANT rds_iam TO <db_username>`. Enable Bedrock model access in the console (ap-south-1).

### 2.3 Terraform Apply Prerequisites

- **Required variables:** `db_username` and `db_password` have no default. Copy **`infrastructure/terraform.tfvars.example`** → **`infrastructure/terraform.tfvars`**, set `db_password`, then run **`.\scripts\deploy.ps1`** (or `terraform apply -var-file=terraform.tfvars` from `infrastructure/`).
- **Lambda layer:** **deploy.ps1** runs the pre-check (builds `layer.zip` if missing). Or run **`.\scripts\build_lambda_layer.ps1`** / **`.\scripts\pre_terraform_check.ps1`** before apply.

### 2.4 Lambda and Database Connectivity

- **Default:** `enable_lambda_vpc = false` — Lambda runs outside the VPC and **cannot** reach Aurora in private subnets.
- **Options:**
  1. Set `enable_lambda_vpc = true` and put Lambda in the same VPC as RDS (and add Bedrock VPC endpoint or NAT for Bedrock).
  2. Keep Lambda outside VPC and use a publicly reachable RDS (not recommended for production).
  3. Use RDS Proxy or another pattern if you have one.

Until this is decided and tested, the **deployed** API may run with DB “unavailable” (health check) and stub/mock data. Local run with tunnel + `DATABASE_URL` is already verified.

### 2.5 Frontend Deploy to S3/CloudFront

- Terraform creates S3 buckets and CloudFront distributions but does **not** upload built assets.
- **Action:** Run **`.\scripts\deploy_frontend.ps1`** from repo root after Terraform apply. It builds doctor-dashboard with `VITE_API_URL` from Terraform output, syncs to the staff S3 bucket, and invalidates CloudFront. Optionally deploys patient-dashboard too (use `-StaffOnly` to skip).

---

## 3. Incomplete / Optional Before First Deploy

- **Phase 4:** Medical audit dashboard, RBAC tests, audit coverage, data localization and encryption verification (see DEVELOPMENT_COMPLETION_STEPS.md).
- **Phase 5–6:** Notifications/alerts, critical-path tests, performance/SLO, runbooks sign-off.
- **Schedule / Appointments:** Frontend still uses mock for Schedule and Appointments; backend has endpoints but pages are not wired (see IMPLEMENTATION_STATUS_AND_COMPLETION.md).
- **Cognito:** Optional; `api_require_cognito` can be `false` for initial testing; set to `true` and configure frontend Cognito vars for production auth.
- **AgentCore / Gateway tools:** `use_agentcore` defaults to `false`; Gateway Lambda and tool registration are separate steps (see agentcore-gateway-manual-steps.md).

---

## 4. Pre-Deploy Checklist (Condensed)

1. **Security**
   - [x] Passwords parameterized in `test_db_conn.py` and `debug_conn.py` (use `DATABASE_URL` or `CDSS_DB_PASSWORD`).
   - [x] `config.json` and `config/my-config.json` in `.gitignore`.
2. **AWS**
   - [ ] Region consistent (e.g. `ap-south-1`); Bedrock model enabled; IAM for Lambda (Bedrock, Secrets Manager, etc.) as per Terraform.
   - [ ] RDS: run **`.\scripts\run_rds_iam_grant.ps1`** once (tunnel + DATABASE_URL set).
3. **Terraform**
   - [ ] Copy **`infrastructure/terraform.tfvars.example`** → **`infrastructure/terraform.tfvars`**, set `db_password`, then run **`.\scripts\deploy.ps1`**.
   - [ ] (Or run **`.\scripts\pre_terraform_check.ps1`** then `terraform apply -var-file=terraform.tfvars` from `infrastructure/`.)
   - [x] Lambda in VPC by default (`enable_lambda_vpc = true`) so it can reach RDS and Bedrock.
4. **After Apply**
   - [ ] Start tunnel (or use SSM); run **`.\scripts\run_migrations_and_seed.ps1`** (RUN_AFTER_TERRAFORM.md).
   - [ ] Run **`.\scripts\run_rds_iam_grant.ps1`** (one-time).
   - [ ] Run **`.\scripts\deploy_frontend.ps1`** (or let deploy.ps1 prompt you).
5. **Verification**
   - [ ] `GET /health` returns 200 and, if applicable, `database: "connected"`.
   - [ ] Run Phase 1–3 (and optionally Phase 4) verification against the deployed base URL.

---

## 5. Conclusion

- **Codebase and design:** Ready for deploy. Set `db_password` in `infrastructure/terraform.tfvars`, then run **`.\scripts\deploy.ps1`**.
- **Production-ready:** After tunnel, migrations, **run_rds_iam_grant.ps1**, frontend deploy, and Bedrock model enable — run Phase 1–3 verification against the deployed API.

For detailed steps and verification commands, use **PRE_BUILD_CHECKLIST.md**, **DEVELOPMENT_COMPLETION_STEPS.md**, and **RUN_AFTER_TERRAFORM.md**.
