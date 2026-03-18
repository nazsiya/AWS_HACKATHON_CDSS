# Testing the CDSS API and Frontend

Three ways to test and see output: **local handler**, **frontend app**, and **deployed API (curl)**.

---

## 0. Quick: Verify API and Bedrock

Use this checklist to confirm both the REST API and the Bedrock-backed agent work.

### A. Verify API (all routes)

**Local, no DB, no AWS:**

```powershell
cd D:\AI_Hackathon_CDSS
python scripts/test_api_local.py
```

**Expected:** All lines show `Status: 200` (or 404 for get-by-id). POST /agent returns 200 with a body containing `intent`, `data`, `safety_disclaimer` (Bedrock may be fallback if not configured).

**With real DB (e.g. via tunnel):** Set `DATABASE_URL` or run tunnel + seed first, then run the same command to see real data.

**Deployed API (curl):** Replace `YOUR_API_ID` with your API Gateway ID (Terraform output `api_gateway_cdss_url` or similar).

```powershell
$BASE = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev/api"
curl -s "$BASE/../health" | jq .
curl -s "$BASE/v1/patients" | jq .
curl -s "$BASE/v1/resources" | jq .
```

If Cognito is enabled, add: `-H "Authorization: Bearer $TOKEN"`.

### B. Verify Bedrock connectivity (AWS only)

Confirms your AWS credentials and region can call Bedrock (no CDSS code).

```powershell
cd D:\AI_Hackathon_CDSS
python scripts/test_bedrock.py
```

**Expected:** Prints "Success! Response: ..." from the model. If you see `AccessDeniedException`, enable model access in the Bedrock console for your region (ap-south-1).

### C. Verify POST /agent with Bedrock (Supervisor + Converse)

The Supervisor uses **BEDROCK_CONFIG_SECRET_NAME** for intent classification and for "general" chat. Without it, intent falls back to keywords and chat returns a fallback message.

**Option 1 – Local with Bedrock secret**

1. Ensure the Bedrock config secret exists in AWS (Terraform creates `cdss-dev/bedrock-config`).
2. Set env and run the local API test, then call POST /agent:

```powershell
cd D:\AI_Hackathon_CDSS
$env:AWS_REGION = "ap-south-1"
$env:BEDROCK_CONFIG_SECRET_NAME = "cdss-dev/bedrock-config"
python scripts/test_api_local.py
```

Look at the **POST /agent** line: `source` in the body should still be `local`; if Bedrock is used for classification or chat, you may see a real model reply in `data.reply`.

**Option 2 – Local server + curl POST /agent**

1. Terminal 1 – start local API server (with optional Bedrock):

```powershell
cd D:\AI_Hackathon_CDSS
$env:AWS_REGION = "ap-south-1"
$env:BEDROCK_CONFIG_SECRET_NAME = "cdss-dev/bedrock-config"
python scripts/run_api_local.py
```

2. Terminal 2 – call POST /agent:

```powershell
curl -s -X POST http://localhost:8080/agent -H "Content-Type: application/json" -d "{\"message\": \"What surgeries are scheduled today?\"}" | jq .
```

**Expected:** `statusCode: 200`, body with `intent`, `agent`, `data` (e.g. `data.reply` or delegated agent data), `safety_disclaimer`, `source`, `duration_ms`. If Bedrock is not set or fails, you still get 200 with a fallback reply.

**Option 3 – Deployed API**

```powershell
curl -s -X POST "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev/agent" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{"message": "List today'\''s surgeries"}' | jq .
```

### D. Summary

| What to verify        | Command / step |
|-----------------------|----------------|
| All API routes        | `python scripts/test_api_local.py` |
| Health + REST (deployed) | `curl .../health` and `curl .../api/v1/patients` |
| Bedrock AWS connectivity | `python scripts/test_bedrock.py` |
| POST /agent (Bedrock) | Set `BEDROCK_CONFIG_SECRET_NAME`, run `run_api_local.py`, then `curl -X POST http://localhost:8080/agent -d '{"message":"..."}'` |
| Frontend → API        | `run_api_local.py` + frontend with `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false` |

---

## 1. Test handlers locally (no deploy)

Run the router and all agent handlers on your machine with mock API Gateway events.

**From repo root:**

```bash
python scripts/test_api_local.py
```

**What it does:** Calls the router with doctor/admin claims and exercises:

- `GET /api/v1/patients` and `GET /api/v1/patients/PT-1001`
- `GET /api/v1/surgeries` and `GET /api/v1/surgeries/SRG-001`
- `GET /api/v1/resources`, `GET /api/v1/medications`, `GET /api/v1/schedule`
- `GET /api/v1/admin/audit`, `users`, `config`, `analytics`, `resources`

**Expected:** Each line shows `Status: 200` (or 404 for get-by-id when DB is empty) and a short JSON body. Without `DATABASE_URL` or `RDS_CONFIG_SECRET_NAME`, the script mocks the DB so all routes return 200 with empty data. With a real DB, set `DATABASE_URL` or `RDS_CONFIG_SECRET_NAME` and run again.

**Run with PYTHONPATH:** From repo root, set `PYTHONPATH=src` (e.g. `PYTHONPATH=src python scripts/test_api_local.py` on Unix, or `$env:PYTHONPATH="src"; python scripts/test_api_local.py` on PowerShell).

**Optional – test a single path:** In Python:

```python
import sys
sys.path.insert(0, "src")
from cdss.api.handlers.router import handler as router_handler

event = {
    "httpMethod": "GET",
    "path": "/dev/api/v1/patients",
    "pathParameters": {"proxy": "v1/patients"},
    "requestContext": {"authorizer": {"claims": {"custom:role": "doctor", "sub": "1", "email": "d@test.com"}}},
}
print(router_handler(event, None))
```

---

## 2. Test via the frontend (Staff app)

Use the React app with **mock mode off** so it calls your API.

### Option A – API not deployed yet (local Lambda not possible from browser)

Keep **mock mode on** to use in-app mock data:

```bash
cd frontend/apps/doctor-dashboard
npm run dev
```

Open http://localhost:5173. Log in with local mock credentials (contact team for demo access). You’ll see mock patients, surgeries, admin audit, etc., with no backend.

### Option A.5 – Local API server + frontend (no AWS deploy)

Run the CDSS API locally and point the frontend at it:

1. **Terminal 1 – start local API server** (from repo root): `PYTHONPATH=src python scripts/run_api_local.py`. Server runs at http://localhost:8080. Without `DATABASE_URL`, it uses a mocked DB (empty data).
2. **Terminal 2 – frontend** with env to use local API: in `frontend/apps/doctor-dashboard` create `.env.local` with `VITE_API_URL=http://localhost:8080` and `VITE_USE_MOCK=false`, then `npm run dev`. Open http://localhost:5173; the app will call the local API (empty lists or mock login).

### Option B – API deployed; frontend calls real API

1. Deploy infrastructure (e.g. `cd infrastructure && terraform apply`).
2. Create a `.env.local` in `frontend/apps/doctor-dashboard/`:

   ```env
   VITE_API_URL=https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev
   VITE_USE_MOCK=false
   VITE_COGNITO_USER_POOL_ID=ap-south-1_xxxxx
   VITE_COGNITO_CLIENT_ID=xxxxx
   VITE_COGNITO_REGION=ap-south-1
   ```

   Use the Terraform outputs: `api_gateway_url` (no `/api`), `cognito_user_pool_id`, `cognito_staff_client_id`.

3. Create a user in Cognito and set the **role** custom attribute (e.g. `doctor` or `admin`).
4. Run the app and log in with that user:

   ```bash
   cd frontend/apps/doctor-dashboard
   npm run dev
   ```

5. Use the UI: Patients, Surgery, Admin (Audit, Users, Config, Analytics, Resources), Medications. All of these will hit the deployed API and you’ll see real responses (stub data until RDS is wired).

---

## 3. Test deployed API with curl

After `terraform apply`, use the CDSS API base URL from output `api_gateway_cdss_url` (e.g. `https://xxx.execute-api.ap-south-1.amazonaws.com/dev/api/`).

### If Cognito is **disabled** on the API (`api_require_cognito = false`)

```bash
BASE="https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev/api"

curl -s "${BASE}/v1/patients" | jq .
curl -s "${BASE}/v1/patients/PT-1001" | jq .
curl -s "${BASE}/v1/surgeries" | jq .
curl -s "${BASE}/v1/resources" | jq .
curl -s "${BASE}/v1/medications" | jq .
curl -s "${BASE}/v1/schedule" | jq .
```

Admin routes (audit, users, config, analytics) need a JWT; use the frontend or Postman with Cognito login to get a token.

### If Cognito is **enabled** (`api_require_cognito = true`)

You must send a valid Cognito Id token:

```bash
# Get token (e.g. from browser after login, or use AWS Amplify / Cognito auth flow),
# then:
TOKEN="eyJraWQ..."

curl -s -H "Authorization: Bearer $TOKEN" "${BASE}/v1/patients" | jq .
curl -s -H "Authorization: Bearer $TOKEN" "${BASE}/v1/admin/audit" | jq .
```

**Health (no auth):**

```bash
curl -s "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev/health" | jq .
```

---

## Quick reference

| Goal                         | Use |
|-----------------------------|-----|
| See API responses, no AWS   | `PYTHONPATH=src python scripts/test_api_local.py` |
| Run local API server        | `PYTHONPATH=src python scripts/run_api_local.py` |
| Use the UI with fake data   | `npm run dev` with mock mode (default) |
| Use the UI with local API   | Start `run_api_local.py`, then `VITE_API_URL=http://localhost:8080` `VITE_USE_MOCK=false` and `npm run dev` |
| Use the UI with deployed API| Set `VITE_API_URL`, `VITE_USE_MOCK=false`, Cognito env, then `npm run dev` |
| Call API from command line  | `curl` to `.../dev/api/v1/...` (and token if Cognito is on) |

---

## 4. Role-based API testing (Phase 3)

Repeatable, non-UI tests for RBAC and endpoint correctness using Cognito tokens.

### Token acquisition

**Get a Cognito id_token (staff or patient app client):**

```powershell
cd D:\AI_Hackathon_CDSS

# From Terraform: cognito_user_pool_id, cognito_staff_client_id (or cognito_patient_client_id)
$env:COGNITO_USER_POOL_ID = "ap-south-1_xxxxx"
$env:COGNITO_CLIENT_ID = "xxxxx"   # or COGNITO_STAFF_CLIENT_ID / COGNITO_PATIENT_CLIENT_ID
$env:AWS_REGION = "ap-south-1"
python scripts/auth/get_token.py --username "dr.test@hospital.in" --password "YourPassword"
```

For **patient** role, use the patient portal client:

```powershell
$env:COGNITO_CLIENT_ID = ""
python scripts/auth/get_token.py --username "user@example.com" --password "<set in env>" --client-type patient
```

**CI-friendly:** Set `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `AWS_REGION`, `TEST_USERNAME`, `TEST_PASSWORD`; run `python scripts/auth/get_token.py`. Use `--json` for JSON output.

### Decode JWT and verify role

```powershell
python scripts/auth/get_token.py -u user -p pass | python scripts/auth/decode_jwt.py -
python scripts/auth/decode_jwt.py "eyJ..." --require-role -q
```

### RBAC matrix (deployed API)

Infer role from JWT and assert expected status codes for key endpoints:

```powershell
$BASE_URL = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev"
$TOKEN = python scripts/auth/get_token.py -u "doctor@test.in" -p "secret"
python scripts/api_test_utils/rbac_matrix.py --base-url $BASE_URL --token $TOKEN
```

For **patient** role, pass `--patient-id PT-1001` (the patient’s own id). Env: `BASE_URL`, `TOKEN`, optional `PATIENT_ID`. Options: `-v` verbose, `-q` summary only.

---

## WebSocket (Phase 5): JWT auth and test client

The WebSocket API uses a **Lambda REQUEST authorizer** on `$connect` that validates a Cognito JWT passed as `?token=`. The handler entrypoint is `handler.lambda_handler` (Terraform: `handler.lambda_handler`).

### Build authorizer zip (before first deploy with authorizer)

When `enable_websocket_authorizer` is true, run once from repo root so the Lambda zip exists:

```powershell
python scripts/build_websocket_authorizer.py
```

Then run `terraform apply` from the **infrastructure/** directory (`cd infrastructure`), not from the repo root. The zip is written to `infrastructure/websocket_authorizer_lambda.zip` (gitignored).

### Connect with token

Get a token, then connect with `token` and optional `doctor_id` in the query string:

```powershell
$TOKEN = python scripts/auth/get_token.py -u "doctor@hospital.in" -p "YourPassword"
$env:WS_URL = "wss://YOUR_WS_API_ID.execute-api.ap-south-1.amazonaws.com/dev"
$env:WS_TOKEN = $TOKEN
python scripts/ws/ws_client.py
```

**Expected:** Client connects, sends `subscribe_surgery`, `subscribe_patient`, `checklist_update`; receives echoed acknowledgements; exits with "OK".

### No-auth (authorizer disabled)

When `enable_websocket_authorizer = false` (e.g. local testing):

```powershell
python scripts/ws/ws_client.py --no-auth --url wss://YOUR_WS_API_ID/.../dev
```

### Verification script

```powershell
python scripts/ws/verify_websocket.py --url wss://... --token $TOKEN
```

Optional: `--no-auth`, `--skip-client` (only check that connect without token is rejected when authorizer is on).

---

## Phase 6 – Async (EventBridge/SQS/DLQ/SNS), RAG, MCP adapter

### One-shot validation (no AWS)

Run all Phase 6 checks locally (EventBridge detail build, RAG dry-run, MCP adapter):

```powershell
python scripts/test_async_rag_mcp.py
```

**Expected:** `[PASS]` for async build_detail, RAG ingest dry-run, RAG query similarity, MCP hospital, MCP ABDM.

### Async: EventBridge MCP events to SQS

Events with source `cdss.agents` are routed to the `agent_events` SQS queue (see `infrastructure/notifications.tf`). To publish and inspect:

```powershell
$env:EVENT_BUS_NAME = "cdss-events-dev"   # Terraform output: cdss_event_bus_name
$env:AWS_REGION = "ap-south-1"
python scripts/async/put_eventbridge_event.py patient_profile_request '{"patient_id":"PT-1001"}'
```

Poll main queue and DLQ (set `SQS_QUEUE_URL` and `SQS_DLQ_URL` from Terraform outputs `sqs_queue_url`, `sqs_dlq_url`):

```powershell
$env:SQS_QUEUE_URL = "https://sqs.ap-south-1.amazonaws.com/ACCOUNT/cdss-dev-agent-events"
$env:SQS_DLQ_URL = "https://sqs.ap-south-1.amazonaws.com/ACCOUNT/cdss-dev-agent-events-dlq"
python scripts/async/poll_sqs_and_dlq.py --max 5
```

### SNS (patient reminders, doctor escalations)

```powershell
$env:SNS_TOPIC_PATIENT_REMINDERS_ARN = "arn:aws:sns:..."
$env:SNS_TOPIC_DOCTOR_ESCALATIONS_ARN = "arn:aws:sns:..."
python scripts/notify/test_sns_publish.py
```

### RAG: embeddings ingest and similarity

Local JSON store (no Bedrock):

```powershell
python scripts/rag/ingest_embeddings.py --dry-run --output embeddings.json
python scripts/rag/query_similarity.py --store embeddings.json --query "wound care" --top 3 --dry-run
```

With Bedrock (Titan Embed): omit `--dry-run` and set `AWS_REGION` and model access.

### MCP adapter (Hospital, ABDM)

Offline tests (stubbed adapter):

```powershell
python scripts/mcp/test_hospital_mcp.py
python scripts/mcp/test_abdm_mcp.py
```

These assert response shape and safe error fallback for unknown or empty inputs.
