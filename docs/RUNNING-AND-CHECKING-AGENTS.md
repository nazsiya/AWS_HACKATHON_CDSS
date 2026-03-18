# Running and Checking CDSS Agents — Detailed Steps

This guide covers how to run and verify all CDSS agents locally and (optionally) when deployed. The system uses a **Supervisor** that classifies intents and delegates to domain agents: **Patient**, **Surgery**, **Resource**, **Scheduling**, and **Engagement**. Optional: **AgentCore** runtime and **Gateway** for MCP tools.

---

## 1. Overview of Agents

| Agent | Role | Exposed via | Notes |
|------|------|-------------|--------|
| **Supervisor** | Intent classification + routing | `POST /agent`, `POST /api/v1/supervisor` | Uses Bedrock (or keyword fallback) to classify, then delegates |
| **Patient** | Patient list, detail, history | `GET /api/v1/patients`, `GET /api/v1/patients/{id}` | Backed by `src/cdss/api/handlers/patient.py` |
| **Surgery** | Surgeries, checklists, guidance | `GET /api/v1/surgeries`, `GET /api/v1/surgeries/{id}` | Backed by `src/cdss/api/handlers/surgery.py` |
| **Resource** | OTs, equipment, staff | `GET /api/v1/resources` | Backed by `src/cdss/api/handlers/resource.py` |
| **Scheduling** | Slots, schedule | `GET /api/v1/schedule` | Backed by `src/cdss/api/handlers/scheduling.py` |
| **Engagement** | Medications, reminders, consultations | `GET /api/v1/medications`, reminders/consultations APIs | Backed by `src/cdss/api/handlers/engagement.py` |
| **Hospitals / Triage** | Hospital lookup, severity assessment | `POST /api/v1/hospitals`, `POST /api/v1/triage` | Invoked by Supervisor when intent matches |

When **USE_AGENTCORE=true** and **AGENT_RUNTIME_ARN** is set, the Supervisor can invoke the **AgentCore Runtime** instead of local handlers. The **AgentCore Gateway** (optional) exposes MCP tools (e.g. hospital data) to agents.

---

## 2. Prerequisites

- **Python 3.10+** (repo root and `src` on `PYTHONPATH` or `pip install -e .`)
- **Node.js 18+** (for frontend)
- **AWS credentials** (optional for local mock; required for Bedrock and deployed API): `aws configure` or `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- **Optional:** `DATABASE_URL` or `RDS_CONFIG_SECRET_NAME` for real Aurora data; otherwise handlers use mocked/empty data
- **Optional:** `BEDROCK_CONFIG_SECRET_NAME` (e.g. `cdss-dev/bedrock-config`) for intent classification and chat via Bedrock

All commands below assume you are at the **repo root**: `D:\AI_Hackathon_CDSS` (Windows) or `/path/to/AI_Hackathon_CDSS`.

---

## 3. Step-by-Step: Run and Check Agents

### Step 1 — Verify API and All Agent-Backed Routes (No AWS Required)

This runs the Lambda router locally with mock API Gateway events and exercises every agent-backed route.

**PowerShell (repo root):**

```powershell
cd D:\AI_Hackathon_CDSS
python scripts/test_api_local.py
```

**What it does:**

- Calls the router with doctor/admin claims for:
  - `GET /api/v1/patients`, `GET /api/v1/patients/PT-1001` (Patient agent)
  - `GET /api/v1/surgeries`, `GET /api/v1/surgeries/SRG-001` (Surgery agent)
  - `GET /api/v1/resources` (Resource agent)
  - `GET /api/v1/medications`, `GET /api/v1/schedule` (Engagement, Scheduling)
  - `GET /api/v1/admin/*` (Admin)
  - `GET /dashboard` (Dashboard)
  - **`POST /agent`** (Supervisor — intent classification + delegation to local agents)

**Expected:** Each line shows `Status: 200` (or 404 for get-by-id when DB is empty). `POST /agent` returns a JSON body with `intent`, `agent`, `data`, `safety_disclaimer`, `source`, `duration_ms`. Without Bedrock, `source` is `local` and intent uses keyword fallback.

**With real DB:** Set `DATABASE_URL` or `RDS_CONFIG_SECRET_NAME` (and ensure DB is reachable, e.g. SSM tunnel), then run the same command again.

---

### Testing agents with the database connected (Aurora via SSM tunnel)

To run and check agents **using real data from Aurora**, the DB must be reachable. From your PC, Aurora is only reachable through the **SSM tunnel** (see [database-connection-guide.md](./database-connection-guide.md)).

**1. Terminal 1 – start the tunnel (leave it open):**

```powershell
cd D:\AI_Hackathon_CDSS
.\scripts\start_ssm_tunnel.ps1
```

Wait until you see: `Port 5433 opened for sessionId ...`

**2. Terminal 2 – set DATABASE_URL and run the API test:**

```powershell
cd D:\AI_Hackathon_CDSS
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
$env:PYTHONPATH = "src"
python scripts/test_api_local.py
```

Replace `YOUR_PASSWORD` with your Aurora master password (same as `db_password` in Terraform). Database name must be **`cdssdb`**.

**Expected:** Banner says "using DATABASE_URL / RDS config". All routes return 200; patients, surgeries, medications, schedule, etc. come from the DB (or 404 if no rows). `POST /agent` (Supervisor) delegates to agents that read/write the same DB.

**3. Optional – run the local API server and call POST /agent with DB:**

In Terminal 2 (tunnel still running in Terminal 1):

```powershell
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```

In a **third** terminal, call the Supervisor:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "List patients"}'
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "What surgeries are scheduled?"}'
```

Responses will reflect real DB data. You can also point the frontend at `http://localhost:8080` (`VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false`) so the UI uses the same DB-backed API.

**Troubleshooting:** If you see "Audit log DB write failed" or "Patient handler error" with connection errors, the tunnel is not running or `DATABASE_URL` is wrong (must be `localhost:5433`, not the Aurora hostname). See [database-connection-guide.md §5](./database-connection-guide.md#5-running-test_api_localpy-and-other-scripts-with-real-db).

---

### Testing Bedrock AI with the database

To test **Bedrock** (intent classification + chat) **and** the **database** together: use the tunnel, set both `DATABASE_URL` and `BEDROCK_CONFIG_SECRET_NAME`, then run the local API and call `POST /agent`. The Supervisor will use Bedrock to classify intents and (for "general" intent) to reply; delegated agents (patient, surgery, etc.) will read/write Aurora.

**Prerequisites:** AWS credentials configured (`aws configure` or env vars). The Bedrock config secret must exist in AWS (Terraform creates `cdss-dev/bedrock-config`). Ensure Bedrock model access is enabled in the console for your region (e.g. ap-south-1).

**1. Terminal 1 – start the SSM tunnel (leave it open):**

```powershell
cd D:\AI_Hackathon_CDSS
.\scripts\start_ssm_tunnel.ps1
```

Wait until you see: `Port 5433 opened for sessionId ...`

**2. Terminal 2 – set DATABASE_URL + Bedrock secret and start the API server:**

```powershell
cd D:\AI_Hackathon_CDSS
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
$env:AWS_REGION = "ap-south-1"
$env:BEDROCK_CONFIG_SECRET_NAME = "cdss-dev/bedrock-config"
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```

Replace `YOUR_PASSWORD` with your Aurora master password. You should see: `CDSS local API at http://localhost:8080 (mock DB: false)`.

**3. Terminal 3 – call POST /agent (Bedrock + DB):**

```powershell
# Intent classified by Bedrock; agent data from DB
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "What surgeries are scheduled today?"}'
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "List all patients"}'
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "Hello, how can you help?"}'
```

**Expected:** Each response has `intent` (from Bedrock classification), `agent`, `data` (from DB-backed handlers or Bedrock reply for "general"), `safety_disclaimer`, `source: "local"`, `duration_ms`. For patient/surgery/resource intents, `data` reflects real Aurora data.

**Optional:** Run `python scripts/test_bedrock.py` first to confirm Bedrock connectivity; then run `python scripts/test_api_local.py` with the same env vars (tunnel + `DATABASE_URL` + `BEDROCK_CONFIG_SECRET_NAME`) to hit all routes including `POST /agent` with Bedrock and DB in one script.

**Interactive chat (type input, get Bedrock + DB answers):** With the API server running (Terminal 2 above), in a **third** terminal run:

```powershell
cd D:\AI_Hackathon_CDSS
python scripts/chat_agent_interactive.py
```

Then type a message and press Enter; each line is sent to `POST /agent`, and the reply (from Bedrock and/or DB-backed agents) is printed. Empty line or Ctrl+C to exit.

---

Confirms AWS credentials and Bedrock model access in your region (no CDSS agents, just Bedrock).

**PowerShell:**

```powershell
cd D:\AI_Hackathon_CDSS
python scripts/test_bedrock.py
```

**Expected:** Prints `Success! Response: ...` from the model. If you see `AccessDeniedException`, enable model access in the Bedrock console for your region (e.g. ap-south-1).

---

### Step 3 — Run Local API Server and Test POST /agent (Supervisor + Agents)

Run the CDSS API as an HTTP server, then call `POST /agent` to exercise the Supervisor and delegated agents.

**Terminal 1 — Start local API server:**

**PowerShell:**

```powershell
cd D:\AI_Hackathon_CDSS
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```

**Optional (Bedrock intent classification + chat):**

```powershell
$env:AWS_REGION = "ap-south-1"
$env:BEDROCK_CONFIG_SECRET_NAME = "cdss-dev/bedrock-config"
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```

You should see: `CDSS local API at http://localhost:8080 (mock DB: true/false)`.

**Terminal 2 — Call POST /agent:**

**PowerShell:**

```powershell
# Surgery intent (keyword or Bedrock)
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "What surgeries are scheduled today?"}'

# Patient intent
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "Show me patient PT-1001"}'

# General chat (if Bedrock configured)
Invoke-RestMethod -Uri "http://localhost:8080/agent" -Method POST -ContentType "application/json" -Body '{"message": "Hello"}'
```

**Or with curl (if available):**

```bash
curl -s -X POST http://localhost:8080/agent -H "Content-Type: application/json" -d "{\"message\": \"What surgeries are scheduled today?\"}"
```

**Expected:** `statusCode: 200`, body with `intent`, `agent`, `data` (e.g. `data.reply` or delegated agent payload), `safety_disclaimer`, `source` (`local` or `agentcore`), `duration_ms`. If Bedrock is not set or fails, you still get 200 with keyword-based intent and local delegation.

---

### Step 4 — Test Agents via Frontend

**Option A — Frontend with mock data (no backend):**

```powershell
cd D:\AI_Hackathon_CDSS\frontend
npm run dev:dashboard
```

Open http://localhost:5173. Log in with your local mock or Cognito credentials (see frontend setup; do not commit real passwords).

**Option B — Frontend with local API (agents behind API):**

1. Start the local API server (Step 3, Terminal 1).
2. In `frontend/apps/doctor-dashboard`, create or edit `.env.local`:

   ```
   VITE_API_URL=http://localhost:8080
   VITE_USE_MOCK=false
   ```

3. Start the frontend:

   ```powershell
   cd D:\AI_Hackathon_CDSS\frontend
   npm run dev:dashboard
   ```

4. Open http://localhost:5173. The app will call the local API; Patient, Surgery, Resource, Schedule, and Engagement data come from the router and agent handlers. Use the AI/chat feature to hit `POST /agent` (Supervisor).

---

### Step 5 — Optional: AgentCore Runtime and Gateway

Use this when you want the Supervisor to call an **AgentCore Runtime** instead of (or in addition to) local handlers.

**5a. Create an agent in AWS (toolkit):**

```powershell
cd D:\AI_Hackathon_CDSS\agentcore\agent
pip install bedrock-agentcore-starter-toolkit bedrock-agentcore
agentcore create
# Follow prompts: framework, project name, template, region (e.g. ap-south-1)
agentcore dev
# In another terminal: curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "Hello"}'
# Stop with Ctrl+C, then:
agentcore launch
```

Note the **Agent Runtime ARN** from the output.

**5b. Gateway (MCP tools):**

```powershell
cd D:\AI_Hackathon_CDSS
$arn = (cd infrastructure; terraform output -raw gateway_get_hospitals_lambda_arn)
python scripts/setup_agentcore_gateway.py $arn
```

Then in AWS Console: **Bedrock → AgentCore → Gateways → [your gateway] → Targets → Add target** and attach the Lambda. See [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md).

**5c. Wire CDSS to AgentCore:**

In `infrastructure/terraform.tfvars` (create if needed, gitignored):

```hcl
use_agentcore     = true
agent_runtime_arn = "<ARN from 5a>"
```

Then:

```powershell
cd D:\AI_Hackathon_CDSS\infrastructure
terraform apply
```

After deploy, the CDSS Lambda will have `USE_AGENTCORE=true` and `AGENT_RUNTIME_ARN` set. `POST /agent` and `POST /api/v1/supervisor` will invoke the AgentCore Runtime when configured.

---

### Step 6 — Optional: Deployed API (Cognito Optional)

After `terraform apply`, use the API Gateway URL from Terraform output (e.g. `api_gateway_cdss_url`).

**Health (no auth):**

```powershell
$BASE = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev"
Invoke-RestMethod -Uri "$BASE/health"
```

**REST routes (if Cognito disabled):**

```powershell
$API = "$BASE/api"
Invoke-RestMethod -Uri "$API/v1/patients"
Invoke-RestMethod -Uri "$API/v1/surgeries"
Invoke-RestMethod -Uri "$API/v1/resources"
```

**POST /agent (if Cognito enabled, pass token):**

```powershell
$token = "YOUR_COGNITO_ID_TOKEN"
Invoke-RestMethod -Uri "$BASE/agent" -Method POST -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body '{"message": "List today surgeries"}'
```

---

## 4. Quick Reference

| Goal | Command / step |
|------|-----------------|
| **Check all API routes and POST /agent** | `python scripts/test_api_local.py` (from repo root) |
| **Check Bedrock only** | `python scripts/test_bedrock.py` |
| **Test Bedrock + database** | Tunnel running → `DATABASE_URL=...localhost:5433/cdssdb` + `BEDROCK_CONFIG_SECRET_NAME=cdss-dev/bedrock-config` + `AWS_REGION=ap-south-1` → `run_api_local.py` → `POST /agent` (see § Testing Bedrock AI with the database) |
| **Interactive chat (Bedrock + DB)** | API server running → `python scripts/chat_agent_interactive.py` → type messages, see replies |
| **Run local API server** | `$env:PYTHONPATH="src"; python scripts/run_api_local.py` |
| **Test Supervisor (POST /agent)** | Server running → `POST http://localhost:8080/agent` with `{"message": "..."}` |
| **Frontend with mock data** | `cd frontend; npm run dev:dashboard` |
| **Frontend with local API** | Start `run_api_local.py`, set `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false`, then `npm run dev:dashboard` |
| **Create AgentCore agent** | `agentcore create` → `agentcore dev` (test) → `agentcore launch` (deploy) |
| **Setup AgentCore Gateway** | `python scripts/setup_agentcore_gateway.py <lambda_arn>` then add Lambda target in Console |
| **Use deployed API** | `Invoke-RestMethod` or `curl` to `https://YOUR_API_ID.../dev/...` with optional Bearer token |

---

## 5. Troubleshooting

| Issue | Action |
|-------|--------|
| `ModuleNotFoundError: cdss` | Run from repo root and set `PYTHONPATH=src`, or `pip install -e .` |
| `POST /agent` returns 200 but generic reply | Set `BEDROCK_CONFIG_SECRET_NAME` for intent classification; otherwise keyword fallback is used. |
| DB connection errors when using Bedrock + DB | Start SSM tunnel first; set `DATABASE_URL` to `postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb` (not Aurora hostname). See [database-connection-guide.md](./database-connection-guide.md). |
| `AccessDeniedException` (Bedrock) | Enable model access in Bedrock console for your region and account. |
| Local server connection refused | Ensure `run_api_local.py` is running and nothing else is using port 8080. |
| AgentCore not invoked | Ensure `USE_AGENTCORE=true` and `AGENT_RUNTIME_ARN` are set on the Lambda (Terraform). |
| Gateway tool not found | In Console, add Lambda as target; tool name is `{target_name}___tool_name`. |

For more detail, see [TESTING.md](./TESTING.md), [agentcore-implementation-plan.md](./agentcore-implementation-plan.md), and [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md).
