# Pre-Build Checklist — Keys, APIs & Config

Use this **before** starting Phase 1 (or any build) so you can set the right keys, APIs, and config once. This avoids conflicts between local vs deployed, frontend vs backend, and different environments.

---

## 1. What You Need to Provide or Update

### 1.1 AWS account & region

| Item | Where to set | Example / Notes |
|------|----------------|-----------------|
| **AWS Region** | Env: `AWS_REGION` or `AWS_DEFAULT_REGION` | `ap-south-1` (Mumbai) — must match PROJECT_REFERENCE.md |
| **AWS Account ID** | Not set in code; used in ARNs | `746412758276` (from PROJECT_REFERENCE) |
| **AWS credentials** | `aws configure` or env: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Must be able to: read Secrets Manager, invoke Bedrock, (optional) access RDS |

**Conflict to avoid:** If your infra is in a different region (e.g. `us-east-1`), either move to `ap-south-1` or update **every** reference to region in PROJECT_REFERENCE.md, gateway-config.json, and frontend env.

---

### 1.2 AWS Secrets Manager (backend / Lambda)

The backend expects **secret names** via env; the **values** live in AWS Secrets Manager. Do **not** put secret values in `.env` or in code.

| Secret name (env var) | Required for | Secret JSON shape | You need to |
|------------------------|-------------|--------------------|-------------|
| `RDS_CONFIG_SECRET_NAME` | DB (Aurora from Lambda) | `{ "host": "...", "port": 5432, "database": "cdssdb", "username": "cdssadmin", "region": "ap-south-1" }` | Create/update in AWS (Terraform or Console). For **local** runs use the bastion tunnel and `DATABASE_URL=...@localhost:5433/cdssdb` (see §1.3). |
| `BEDROCK_CONFIG_SECRET_NAME` | Agent/Bedrock | `{ "model_id": "anthropic.claude-3-haiku-20240307-v1:0", "region": "ap-south-1" }` | Create/update in AWS. Model must be enabled in Bedrock console. |
| `CDSS_APP_CONFIG_SECRET_NAME` | Cognito, EventBridge, gateway ARNs (admin, WebSocket) | `{ "cognito_user_pool_id": "ap-south-1_xxxxx", "aws_region": "ap-south-1", "event_bus_name": "cdss-events", "agent_runtime_arn": "arn:...", "gateway_get_hospitals_lambda_arn": "arn:..." }` | **Optional** for local API. Create in AWS when using Cognito RBAC, admin users, or WebSocket authorizer. |

**Current state (from your `all-secrets.json`):** You have `cdss-dev/bedrock-config` and `cdss-dev/rds-config`. You do **not** have `cdss-dev/app-config` listed — add it in AWS if you need Cognito/admin/WebSocket.

**Conflict to avoid:** Secret names must match what you set in env (e.g. `cdss-dev/rds-config`). If Terraform uses a different prefix, set the env var to that full name.

---

### 1.3 Database (production: bastion + Aurora)

All database access uses the **bastion** and **SSM tunnel** to Aurora. There is no local Postgres path.

| Item | Where to set | Example |
|------|----------------|---------|
| **DATABASE_URL** | Second terminal, after starting tunnel (see below) | `postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb` |

1. Start the tunnel: `.\scripts\start_ssm_tunnel.ps1` (leave that terminal open).
2. In another terminal, set `DATABASE_URL` with port **5433** (tunnel port) and the Aurora master password.
3. Run migrations, seed, or the local API as needed. See **docs/database-connection-guide.md** and **docs/BASTION_AND_DB_QUERIES.md**.

---

### 1.4 Frontend: API and auth (doctor-dashboard / patient-dashboard)

The frontend reads from **env** at build time (Vite). Use `.env` in each app or inject via `config/gateway-config.json` / CI.

| Variable | Required | Purpose | Example |
|----------|-----------|---------|---------|
| **VITE_API_URL** | Yes (if not mock) | REST API base URL, no trailing slash | `http://localhost:8080` (local) or `https://xxxx.execute-api.ap-south-1.amazonaws.com/dev` |
| **VITE_USE_MOCK** | No | `"true"` / `"1"` = mock data; else live API | `false` when using real API |
| **VITE_WS_URL** | No | WebSocket URL for real-time updates | `wss://xxxx.execute-api.ap-south-1.amazonaws.com/dev` |
| **VITE_COGNITO_USER_POOL_ID** | For login | Cognito User Pool ID | `ap-south-1_0eRSiDzbY` |
| **VITE_COGNITO_CLIENT_ID** | For login | App client ID (doctor vs patient use different clients) | Doctor: `15hk1uremldsor79jkc7cr866v`, Patient: `14qo2b4sdrjgbdnqietsj9jn3u` |
| **VITE_COGNITO_REGION** | No | Cognito region | `ap-south-1` |

**Where to set:**
- **Local:** `frontend/apps/doctor-dashboard/.env` and `frontend/apps/patient-dashboard/.env` (copy from `.env.example`).
- **Deployed:** Same values are in `config/gateway-config.json` under `frontend.doctorDashboard` and `frontend.patientDashboard` — keep these in sync.

**Conflicts to avoid:**
- `VITE_API_URL` must point to the **same** backend you run (local `http://localhost:8080` vs deployed API Gateway URL). Don’t mix (e.g. frontend on localhost but API URL pointing to AWS).
- Doctor and patient dashboards use **different** `VITE_COGNITO_CLIENT_ID` in your config; keep both IDs correct for each app.

---

### 1.5 API Gateway & WebSocket URLs (deployed)

If you use **deployed** API Gateway and WebSocket API, their URLs must match everywhere:

| Source | What to update |
|--------|----------------|
| **config/gateway-config.json** | `apiGateway.baseUrl`, `apiGateway.cdssApiBase`, `apiGateway.healthUrl`, `websocket.url` |
| **Frontend .env or gateway frontend section** | `VITE_API_URL`, `VITE_WS_URL` must match the same API Gateway / WebSocket URLs |
| **PROJECT_REFERENCE.md** | If you change region or account, update “API Endpoints” and “AWS Configuration” |

Your current `gateway-config.json` has:
- API: `https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev`
- WebSocket: `wss://jcw3vemil9.execute-api.ap-south-1.amazonaws.com/dev`

If you create a **new** API Gateway (e.g. new stack), update **all** of these or the frontend will call the wrong backend.

---

### 1.6 AgentCore / Bedrock (for Phase 1)

| Item | Where | What to do |
|------|--------|------------|
| **Claude 3 Haiku** | AWS Console → Bedrock → Model access | Enable in `ap-south-1` so tool-use works. |
| **Execution role** | IAM | Attach `AmazonBedrockFullAccess` to `AmazonBedrockAgentCoreSDKRuntime-ap-south-1-6eac3e734d` (or your actual AgentCore runtime role name). |
| **Agent ID / Runtime ARN** | PROJECT_REFERENCE.md, app-config secret | Keep in sync with your AgentCore agent and runtime. |

---

## 2. Quick checklist before you run “build” or Phase 1

- [ ] **Region:** `AWS_REGION=ap-south-1` (or consistent everywhere if you use another region).
- [ ] **DB (local):** Either `DATABASE_URL` in `.env` **or** `RDS_CONFIG_SECRET_NAME` + AWS creds for Aurora.
- [ ] **DB (AWS):** Secret `cdss-dev/rds-config` (or your name) exists and has `host`, `port`, `database`, `username`, `region`.
- [ ] **Bedrock:** Secret `cdss-dev/bedrock-config` exists with `model_id` and `region`; Claude 3 Haiku enabled in console.
- [ ] **App config (optional):** If using Cognito/admin/WebSocket, create `cdss-dev/app-config` with `cognito_user_pool_id`, `aws_region`, etc.
- [ ] **Frontend:** For local API: `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false`. For deployed API: `VITE_API_URL` = your API Gateway URL; Cognito IDs match your User Pool and app clients.
- [ ] **Single source of URLs:** gateway-config.json and frontend env point to the **same** API and WebSocket URLs.

---

## 3. Optional: one-place config for your ID

If you want a **single** place to paste your IDs (no secrets), you can keep a **private** file (do not commit) like `config/my-config.json` with:

```json
{
  "aws_region": "ap-south-1",
  "rds_config_secret_name": "cdss-dev/rds-config",
  "bedrock_config_secret_name": "cdss-dev/bedrock-config",
  "app_config_secret_name": "cdss-dev/app-config",
  "cognito_user_pool_id": "ap-south-1_0eRSiDzbY",
  "cognito_staff_client_id": "15hk1uremldsor79jkc7cr866v",
  "cognito_patient_client_id": "14qo2b4sdrjgbdnqietsj9jn3u",
  "api_base_url": "https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev",
  "ws_url": "wss://jcw3vemil9.execute-api.ap-south-1.amazonaws.com/dev"
}
```

Scripts or docs can reference “set env from config/my-config.json” so you update IDs in one place. Never put passwords or API keys in this file.

---

## 4. References

- **Secrets and config:** [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) (§ AWS Configuration & Endpoints, § AWS Secrets Manager).
- **Frontend endpoints:** [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md).
- **Phases and verification:** [DEVELOPMENT_COMPLETION_STEPS.md](DEVELOPMENT_COMPLETION_STEPS.md).
