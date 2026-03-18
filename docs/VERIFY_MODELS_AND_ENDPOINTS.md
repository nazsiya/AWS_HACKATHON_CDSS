# CDSS Models and Endpoints Verification

This document describes how to verify that all **AI models** (Bedrock) are configured and working, and that every **API endpoint** responds correctly.

## Models (Bedrock)

The CDSS uses **Amazon Bedrock** for AI features. A single model is used across:

- **Router/Supervisor**: `POST /agent` (intent classification + chat fallback)
- **AI handler**: `/api/ai/*` and `/api/v1/ai/*` (summarize, entities, prescription, adherence, engagement, resources, surgery-support, translate)
- **Patient summary**: `GET /api/v1/patients/:id` (AI summary when Bedrock is configured)
- **Consultation**: visit summary and entity extraction

### Configuration

- **Preferred**: `BEDROCK_CONFIG_SECRET_NAME` — Secrets Manager secret with JSON: `model_id`, `region`.  
  Example: `model_id`: `apac.amazon.nova-lite-v1:0`, `region`: `ap-south-1`.
- **Override (local)**: `BEDROCK_MODEL_ID` and `AWS_REGION` in `.env` if you are not using the secret.

### Verified model

When the verification script runs with your env (and optional AWS credentials for Secrets Manager):

- **Status**: CONFIGURED  
- **Source**: BEDROCK_CONFIG_SECRET_NAME (or BEDROCK_MODEL_ID)  
- **Model**: `apac.amazon.nova-lite-v1:0` (default)  
- **Region**: `ap-south-1`  
- **Invoke**: Optional live test (reply "OK") when `--skip-bedrock-invoke` is not used.

If the secret is missing or Bedrock is not configured, AI endpoints still respond but return stub or “unavailable” messages.

---

## Endpoints

All endpoints used by the frontend and documented in `docs/FRONTEND_API_ENDPOINTS.md` and `docs/swagger.yaml` are covered by the verification script.

| Category        | Endpoints |
|----------------|-----------|
| Health & core  | `GET /health`, `GET /dashboard`, `POST /agent` |
| Patients       | `GET /api/v1/patients`, `GET /api/v1/patients/{id}` |
| Surgeries      | `GET /api/v1/surgeries`, `GET /api/v1/surgeries/{id}` |
| Medications    | `GET /api/v1/medications` |
| Resources      | `GET /api/v1/resources` |
| Schedule       | `GET /api/v1/schedule` |
| Consultations  | `POST /api/v1/consultations/start`, `POST /api/v1/consultations` |
| Appointments   | `GET /api/v1/appointments` |
| Tasks          | `GET /api/v1/tasks` |
| Terminology    | `GET /api/v1/terminology` |
| Activity       | `POST /api/v1/activity` |
| AI             | `POST /api/v1/ai/summarize`, `POST /api/ai/summarize`, `POST /api/v1/ai/entities`, `POST /api/ai/prescription`, `POST /api/ai/adherence`, `POST /api/ai/engagement`, `POST /api/ai/resources` |
| Admin          | `GET /api/v1/admin/users`, `GET /api/v1/admin/audit`, `GET /api/v1/admin/config`, `GET /api/v1/admin/analytics` (expect 200 or 403 for doctor role) |
| Docs           | `GET /docs/swagger.yaml` |

---

## How to run verification

From the repo root:

```powershell
# Load .env (copy from .env.example and fill)
$env:PYTHONPATH = "src"

# 1) Models only (no Bedrock invoke)
python scripts/verify_models_and_endpoints.py --skip-bedrock-invoke --skip-endpoints

# 2) Models + live Bedrock test (requires AWS credentials + secret)
python scripts/verify_models_and_endpoints.py --skip-endpoints

# 3) All endpoint tests (API server must be running)
# Terminal 1: start API
python scripts/run_api_local.py

# Terminal 2: run verification (default base URL http://localhost:8080)
python scripts/verify_models_and_endpoints.py --skip-bedrock-invoke

# 4) Against deployed API
python scripts/verify_models_and_endpoints.py --base-url "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev" --skip-bedrock-invoke
```

### Exit codes

- `0`: Models and endpoints OK (or models OK and endpoints skipped).
- `1`: Model verification failed (e.g. Bedrock not configured or invoke failed).
- `2`: One or more endpoint tests failed.

---

## Existing tests

- **`scripts/test_ai_endpoints.py`** — In-process tests for AI Chat, Summarize, Entities, Consultation Start (with mock DB). No HTTP server required.  
  Run: `$env:PYTHONPATH="src"; python scripts/test_ai_endpoints.py`
- **`test_api.py`** — Simple HTTP tests for patient summary and chatbot against `http://localhost:8081/api/...`. Adjust port to match your API (e.g. 8080 for `run_api_local.py`).

---

## Summary

- **Models**: One Bedrock model (e.g. `apac.amazon.nova-lite-v1:0`) is used for all AI features; configuration is verified via `BEDROCK_CONFIG_SECRET_NAME` or `BEDROCK_MODEL_ID`.
- **Endpoints**: Every documented route is exercised by `scripts/verify_models_and_endpoints.py`; run it with the API server up to confirm all endpoints are working.
