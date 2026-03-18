# MCP Contracts — External Systems

Phase 2 (Real Integrations) per [DEVELOPMENT_COMPLETION_STEPS.md](DEVELOPMENT_COMPLETION_STEPS.md). Aligns with **requirements.md**: R2 (Patient Management / ABDM), R4 (Resource Optimization), R8 (MCP Communication).

All external URLs and credentials MUST come from **AWS Secrets Manager** or **IAM** only (no `.env` secrets in production). See **Secrets and config** below. **When to set:** Do at **end of development** — see [DEVELOPMENT_COMPLETION_STEPS.md §7](DEVELOPMENT_COMPLETION_STEPS.md#7-end-of-development-mcp--abdm-config-do-last).

---

## 1. Hospital HIS (Hospital Information System) MCP

**Purpose:** Real-time OT status, bed availability, equipment status for Resource Agent and Scheduling Agent (R4, R5).

### Endpoints

| Operation   | Method | Path (example)        | Description                |
|------------|--------|------------------------|----------------------------|
| OT status  | GET    | `/mcp/ot_status`      | List OTs with availability |
| Beds       | GET    | `/mcp/beds`           | Bed count by ward/status   |
| Equipment  | GET    | `/mcp/equipment`      | Equipment list and status  |

Base URL from config: `MCP_HOSPITAL_ENDPOINT` or `cdss/app_config` → `mcp_hospital_endpoint`.

### Authentication

- **Type:** Bearer token (JWT) or API key in header.
- **Header:** `Authorization: Bearer <token>` or `X-API-Key: <key>`.
- Credentials: from Secrets Manager secret (e.g. `cdss-dev/app-config` or `cdss-dev/hospital-mcp-credentials`), never hardcoded.

### Request / Response payloads

**GET /mcp/ot_status**

- Query params (optional): `?date=YYYY-MM-DD`
- Response 200:
```json
{
  "ots": [
    {
      "id": "OT-1",
      "name": "OT 1",
      "status": "available",
      "next_free": "2026-03-08T14:00:00Z",
      "floor": "1",
      "area": "Main"
    }
  ]
}
```

**GET /mcp/beds**

- Query params (optional): `?ward=General&status=available`
- Response 200:
```json
{
  "beds": [
    { "id": "B-1", "ward": "General", "status": "available" }
  ]
}
```

**GET /mcp/equipment**

- Query params (optional): `?type=ventilator`
- Response 200:
```json
{
  "equipment": [
    { "id": "EQ-1", "name": "Ventilator", "status": "available", "quantity": 3 }
  ]
}
```

### Stub behaviour

When `MCP_HOSPITAL_ENDPOINT` is not set or the HTTP call fails, the adapter returns stub data (see `src/cdss/mcp/adapter.py`) so that Resource/Scheduling flows continue without external HIS.

---

## 2. ABDM (Ayushman Bharat Digital Mission) MCP

**Purpose:** Patient identity and EHR lookup for Patient Agent (R2 — Comprehensive Patient Management).

### Endpoints

| Operation       | Method | Path (example)       | Description                    |
|----------------|--------|----------------------|--------------------------------|
| Get record     | GET    | `/gateway/v1/patient/record` or sandbox equivalent | Fetch patient record by ABHA ID / Patient_ID |
| Consent request| POST   | `/gateway/v1/consent/request`  | Create consent for EHR access  |

Base URL from config: `MCP_ABDM_ENDPOINT` or `ABDM_SANDBOX_URL` (sandbox) or `cdss/app_config` → `mcp_abdm_endpoint` / `abdm_sandbox_url`.

### Authentication

- **Type:** ABDM Gateway client credentials (client_id, client_secret) or sandbox token.
- Stored in Secrets Manager (e.g. `cdss-dev/app-config` or `cdss-dev/abdm-credentials`).
- Requests: Bearer token obtained via OAuth2 client-credentials flow against ABDM Gateway, or sandbox API key in header.

### Request / Response payloads

**Get patient record**

- Request: GET with `patient_id` or `abha_id` (or ABHA Address) as query param.
- Response 200 (example):
```json
{
  "patient_id": "PT-1001",
  "abdm_linked": true,
  "abha_id": "1234-5678-9012",
  "summary": "Patient record retrieved from ABDM.",
  "records": [],
  "consent_status": "active"
}
```

**Consent request (create)**

- Request POST body:
```json
{
  "patient_id": "PT-1001",
  "purpose": "Care delivery",
  "hi_types": ["OPConsultation", "Prescription"]
}
```
- Response 200: `{ "consent_request_id": "...", "status": "requested" }`

### Stub / sandbox behaviour

When no ABDM endpoint or credentials are configured, the adapter returns stub: `abdm_linked: false`, `summary: "ABDM integration pending"`. When `ABDM_SANDBOX_URL` (or equivalent) is set, the adapter can call the sandbox API for testing so that patient summary includes real sandbox data in test env (Phase 2.3 verification).

---

## 3. Secrets and config (Phase 2.5)

All external URLs and credentials MUST come from:

- **AWS Secrets Manager** — preferred for URLs and credentials.
- **IAM** — for AWS service access (e.g. Bedrock, RDS auth).

### Required secret keys (documented)

| Secret name (example)     | Keys (example)                          | Used by                |
|---------------------------|------------------------------------------|------------------------|
| `cdss-dev/app-config`     | `mcp_hospital_endpoint`, `mcp_abdm_endpoint`, `abdm_sandbox_url`, `cognito_user_pool_id`, `api_base_url`, … | Router, adapter, admin |
| `cdss-dev/bedrock-config` | `model_id`, `region`                     | Bedrock, AI APIs       |
| `cdss-dev/rds-config`     | `host`, `port`, `database`, `username`  | Lambda, local API     |
| (Optional) `cdss-dev/hospital-mcp-credentials` | `api_key` or `token`        | MCP adapter (Hospital) |
| (Optional) `cdss-dev/abdm-credentials`        | `client_id`, `client_secret` or `sandbox_api_key` | MCP adapter (ABDM)    |

Environment variables used only as **pointers** to secret names (e.g. `CDSS_APP_CONFIG_SECRET_NAME`, `BEDROCK_CONFIG_SECRET_NAME`, `RDS_CONFIG_SECRET_NAME`). No production secrets in `.env` or in code.

### Verification

- Grep/code review: no hardcoded API keys or passwords.
- All MCP and ABDM URLs read from config (Secrets Manager or env that points to secret).

---

## 4. Requirements alignment

| Requirement | Phase 2 step | Implementation |
|-------------|--------------|-----------------|
| **R2** Comprehensive Patient Management | 2.3 Wire Patient Agent to ABDM | Patient handler + Lambda use `get_abdm_record()`; when ABDM sandbox URL is set, adapter returns sandbox data |
| **R4** Real-Time Resource Optimization | 2.4 Wire Resource/Scheduling to OT/staff/equipment | `get_hospital_data(ot_status|beds|equipment)` uses MCP_HOSPITAL_ENDPOINT when set; else stub |
| **R8** MCP Communication & Coordination | 2.1, 2.2 MCP contract + clients | This document (contract); adapter implements configurable HTTP clients |
| **R10** AWS Integration (secrets) | 2.5 Secrets & config | Secrets Manager only; keys documented above |
