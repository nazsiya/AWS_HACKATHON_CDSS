# CDSS Development & Completion Steps

This document consolidates [PROJECT_STATUS.md](PROJECT_STATUS.md), [requirements.md](requirements.md), and [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) into a single, actionable development and completion plan for the Clinical Decision Support System.

> **Before building:** See **[PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md)** for keys, APIs, and config you must set or update to avoid conflicts (AWS region, secrets, frontend env, API Gateway URLs).

---

## 1. Current State Summary


| Area                                 | Status        | Notes                                                                                                                                       |
| ------------------------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **5-Agent Architecture**             | ✅ Done        | Patient, Surgery, Resource, Scheduling, Engagement                                                                                          |
| **Orchestrator & Prompts**           | ✅ Done        | `agentcore/agent/cdssagent/src/main.py`                                                                                                     |
| **11 Clinical Tools (Lambda)**       | ✅ Done        | `infrastructure/gateway_tools_src/lambda_handler.py`                                                                                        |
| **Pydantic Validation & Escalation** | ✅ Done        | Confidence < 0.85 → Senior Review                                                                                                           |
| **RDS Schema & Audit**               | ✅ Done        | Patients, Surgeries, Shifts, Reminders, EventLog, AlertLog                                                                                  |
| **Frontend Base**                    | ✅ Done        | Doctor, Nurse, Patient dashboards in `frontend/apps`                                                                                        |
| **Model Access & IAM**               | ⏳ Pending     | Claude 3 Haiku + BedrockFullAccess on SDK Runtime                                                                                           |
| **Real MCP / ABDM**                  | ✅ In progress | MCP contract doc; configurable adapter + Lambda; stub when no URL set                                                                       |
| **Frontend ↔ API**                   | ✅ Done        | Phase 3 verified: VITE_API_URL + CORS; AIChat shows safety_disclaimer; patient RBAC in backend; local run verified (see Phase 3 run below). |
| **Backend REST API contract**        | ✅ Done        | OpenAPI `docs/swagger.yaml`; Swagger UI at `/api/docs`                                                                                      |
| **AI service APIs**                  | ✅ Done        | `/api/ai/*` (summarize, entities, surgery-support, translate); Nova Lite fallback                                                           |
| **RBAC (Cognito)**                   | ⏳ Pending     | Doctor vs Patient module access enforcement                                                                                                 |
| **Medical Audit Dashboard**          | ⏳ Pending     | Trace review for clinical audit                                                                                                             |
| **Multilingual**                     | ✅ Done        | Hindi + Tamil terminology; GET /api/v1/terminology; translate uses approved terms; agent responds in Hindi/regional via Accept-Language |


> **Dashboard not fully functional?** → See **[DASHBOARD_QUICK_START.md](DASHBOARD_QUICK_START.md)** for env setup (using [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md)), local API + frontend steps, troubleshooting, and what to do after the dashboard works. For a **detailed breakdown of what is implemented vs what is missing** in frontend, backend, and database, see **[IMPLEMENTATION_STATUS_AND_COMPLETION.md](IMPLEMENTATION_STATUS_AND_COMPLETION.md)**.

---

## 2. Requirements-to-Implementation Map


| Req     | Description                                  | Implementation                                                            | Status                                             |
| ------- | -------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------- |
| **R1**  | Role-Based Access (Doctor vs Patient)        | Cognito + module redirect + Doctor_ID/Patient_ID history                  | Partial (logic present; Cognito not finalized)     |
| **R2**  | Comprehensive Patient Management             | Patient Agent + RDS + ABHA + summaries/readiness; ABDM wire when URL set  | ✅ In progress (stub when no URL)                   |
| **R3**  | Surgical Workflow                            | Surgery Agent + tools (classification, checklists, blueprints)            | ✅ Implemented                                      |
| **R4**  | Real-Time Resource Optimization              | Resource Agent + OT/staff/equipment tools                                 | ✅ Implemented                                      |
| **R5**  | Scheduling & Doctor Replacement              | Scheduling Agent + booking/replacement tools                              | ✅ Implemented                                      |
| **R6**  | Patient Engagement & Conversation Analysis   | Engagement Agent + reminders/transcription/summaries                      | ✅ Implemented                                      |
| **R7**  | Multilingual & Cultural Adaptation           | Translation, regional languages, terminology                              | ✅ Done (Hindi + Tamil; approved terminology; GET /api/v1/terminology) |
| **R8**  | MCP Communication & Coordination             | AgentCore + event logs; MCP contract + configurable Hospital/ABDM clients | ✅ In progress (real when endpoint set)             |
| **R9**  | Real-Time Notifications & Emergency Response | Alert engine, drug interaction alerts, escalation                         | Partial (DB/engine in place; channels to be wired) |
| **R10** | AWS Integration & Scalability                | Bedrock, MCP, multi-hospital, data localization, encryption, RBAC, uptime | Partial (core AWS in place; hardening pending)     |


---

## 3. Complete Development & Completion Steps

### Phase 1: Unblock Core Runtime (Priority 1 – Technical)


| Step | Action                                                                                                                                                                 | Owner        | Verification                                       |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------- |
| 1.1  | **Enable Claude 3 Haiku** in AWS Bedrock console (ap-south-1) for tool-use stability                                                                                   | DevOps/Admin | Invoke model from Bedrock; confirm tool calls work |
| 1.2  | **Attach `AmazonBedrockFullAccess`** to execution role `AmazonBedrockAgentCoreSDKRuntime-ap-south-1-6eac3e734d`                                                        | DevOps/Admin | Deploy AgentCore; run end-to-end agent flow        |
| 1.3  | Run **local API** (`python scripts/run_api_local.py`) and **POST /api/v1/agent** with a sample payload; confirm orchestrator routes to correct agent and tools execute | Dev          | Response contains agent reply and tool results     |
| 1.4  | **Deploy Gateway Lambda** with latest `lambda_handler.py`; register tools with AgentCore per `agentcore-gateway-manual-steps.md`                                       | DevOps/Dev   | Agent can call real tools in AWS                   |


### Phase 2: Real Integrations (Priority 1 – Technical)


| Step | Action                                                                                                                        | Owner      | Verification                                        |
| ---- | ----------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------- |
| 2.1  | **Define MCP contract** for each external system (hospital HIS, ABDM, etc.): endpoints, auth, payloads                        | Arch/Dev   | Document in api_reference or design.md              |
| 2.2  | **Implement or adopt MCP clients/servers** that call real hospital/ABDM APIs instead of stubs                                 | Dev        | Unit/integration tests with mock or sandbox         |
| 2.3  | **Wire Patient Agent** to real ABDM (or sandbox) for patient identity and history where applicable                            | Dev        | Patient summary includes real ABDM data in test env |
| 2.4  | **Wire Resource/Scheduling Agents** to real or simulated OT/staff/equipment data sources                                      | Dev        | Availability and conflict checks use live data      |
| 2.5  | **Secrets & config**: Ensure all external URLs and credentials come from **AWS Secrets Manager / IAM** only (no .env secrets) | DevOps/Dev | Security review; no hardcoded keys                  |


**Phase 2 implementation (current):** MCP contract in [MCP_CONTRACTS.md](MCP_CONTRACTS.md); configurable adapter and Lambda ABDM wire; secrets documented in api_reference and MCP_CONTRACTS. Aligns with R2, R4, R8, R10 per requirements.md.

### Phase 2B: Backend API Integration (Autonomous Agent Scope)

This phase is the responsibility of the **Backend API Integration Agent**. It should use [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md) and (when created) [OPENAI_API_ENDPOINTS.md](OPENAI_API_ENDPOINTS.md) as references. All new or changed endpoints must be reflected in the docs and in `/docs/swagger.yaml`.


| Step | Action                                                                                                                                                                                                                                                      | Owner     | Verification                                                                                                                                                |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2B.1 | **Repository analysis**: Scan frontend API usage, backend routes (`src/cdss/api/handlers/*`), database schema, and `/docs` (especially FRONTEND_API_ENDPOINTS.md, OPENAI_API_ENDPOINTS.md, DEVELOPMENT_COMPLETION_STEPS.md)                                 | Agent/Dev | Summary of gaps: missing routes, controllers, or DB ops for frontend-called endpoints                                                                       |
| 2B.2 | **API contract generation**: Generate `**/docs/swagger.yaml`** (OpenAPI 3.x) including authentication endpoints, patient management, doctor management, surgery workflow, resource tracking, scheduling, conversation, and AI service APIs                  | Agent/Dev | `swagger.yaml` exists; all frontend-used endpoints from FRONTEND_API_ENDPOINTS.md are documented with request/response schemas                              |
| 2B.3 | **Verify backend implementation**: For each endpoint, confirm backend controller exists, DB operations are implemented, request validation exists, and response schemas match frontend expectations; if missing, generate controller, service, and DB query | Agent/Dev | Every endpoint in swagger has a matching handler; validation (e.g. Pydantic) and response shape align with frontend (client.js / FRONTEND_API_ENDPOINTS.md) |
| 2B.4 | **AI integration**: Create Bedrock/OpenAI service wrappers for conversation summarization, medical entity extraction, surgery support guidance, and multilingual translation; expose at `**/api/ai/*`**                                                     | Agent/Dev | `POST/GET /api/ai/summarize`, `/api/ai/entities`, `/api/ai/surgery-support`, `/api/ai/translate` (or equivalent) exist and return validated schemas         |
| 2B.5 | **Generate missing components**: If any endpoint is missing, create API routes, controllers, database migrations, models, and schema validations                                                                                                            | Agent/Dev | No 404 for any endpoint listed in FRONTEND_API_ENDPOINTS.md or swagger; migrations applied where new tables/columns needed                                  |
| 2B.6 | **Swagger UI integration**: Serve Swagger documentation at `**/api/docs`** with swagger-ui, OpenAPI validation, and API testing support                                                                                                                     | Agent/Dev | `GET /api/docs` returns Swagger UI; Try-it-out works against local or deployed API                                                                          |
| 2B.7 | **Update documentation**: When new endpoints are added, update OPENAI_API_ENDPOINTS.md (create if missing), FRONTEND_API_ENDPOINTS.md, and DEVELOPMENT_COMPLETION_STEPS.md                                                                                  | Agent/Dev | All public and AI endpoints documented; DEVELOPMENT_COMPLETION_STEPS reflects current phases                                                                |
| 2B.8 | **Output**: Deliver created endpoints list, updated database schema summary, generated swagger file path, and report of missing integrations (if any)                                                                                                       | Agent/Dev | Written output (e.g. in docs or PR description) with the four artifacts                                                                                     |


**Backend API Integration Agent — task checklist (align with prompt):**

1. **Repository analysis** — Scan frontend API usage ([FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md)), backend routes (`src/cdss/api/handlers/*`), database schema, and `/docs`.
2. **API contract generation** — Generate `/docs/swagger.yaml` with authentication, patient, doctor, surgery, resource, scheduling, conversation, and AI service APIs.
3. **Verify backend implementation** — For each endpoint: controller exists, DB operations implemented, request validation present, response schemas match frontend expectations; generate controller/service/DB query if missing.
4. **AI integration** — Create Bedrock/OpenAI wrappers for conversation summarization, medical entity extraction, surgery support guidance, multilingual translation; expose at `/api/ai/*`.
5. **Generate missing components** — Create API routes, controllers, database migrations, models, schema validations as needed.
6. **Swagger UI integration** — Serve docs at `/api/docs` with swagger-ui, OpenAPI validation, and API testing support.
7. **Update documentation** — When new endpoints are added, update OPENAI_API_ENDPOINTS.md (create if missing), FRONTEND_API_ENDPOINTS.md, and DEVELOPMENT_COMPLETION_STEPS.md.
8. **Output** — Provide: created endpoints, updated database schema, generated swagger file path, missing integrations report.

### Phase 3: Frontend & UX (Priority 2)

Frontend-called endpoints are documented in [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md). Phase 2B must ensure backend implementation and swagger match those endpoints.


| Step | Action                                                                                                                                                                                                 | Owner | Verification                                          |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- | ----------------------------------------------------- |
| 3.1  | **Verify frontend → API**: Point React/Vite app at AgentCore API (local or deployed); confirm CORS and auth headers; use [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md) for expected endpoints | Dev   | Dashboard can send request and display agent response |
| 3.2  | **Doctor Module**: List patients, trigger Patient/Surgery/Resource/Scheduling flows, show summaries and audit context                                                                                  | Dev   | Acceptance criteria for R1, R2, R3, R4, R5            |
| 3.3  | **Patient Module**: Restrict to single Patient_ID; show own history, reminders, engagement summary only                                                                                                | Dev   | R1 acceptance: patient cannot access other records    |
| 3.4  | **Multilingual support**: Expand agent responses (and UI labels) to Hindi + at least one regional language; use approved terminology list                                                              | Dev   | R7 acceptance: translation and terminology checks     |
| 3.5  | **Safety disclaimers**: All patient-facing AI summaries and educational content include required disclaimers (per project conventions)                                                                 | Dev   | Review checklist; no unbranded medical advice         |


**Phase 3 (current):** Frontend uses `VITE_API_URL` (e.g. `http://localhost:8080` or `http://localhost:8081` if 8080 is in use) and `VITE_USE_MOCK=false`; CORS enabled. AIChat shows `safety_disclaimer` under AI replies; backend enforces patient role (own record only). See doctor-dashboard `.env.example`.

**Phase 3 run verified:** Local API was started (`$env:PORT="8081"; python scripts/run_api_local.py`); Phase 1.3 verification script ran with `BASE_URL=http://localhost:8081`. Result: **OK** — 200 response, agent reply in body (e.g. patient list), envelope with `intent`, `agent`, `safety_disclaimer`, `correlationId`, `duration_ms`. In-process router test also confirmed GET `/health` and POST `/agent` with `safety_disclaimer`. Use port **8081** if 8080 is occupied; set `VITE_API_URL=http://localhost:8081` in frontend `.env.local` accordingly.

**Phase 3 connectivity check:** Run `scripts/verify_phase3_connectivity.py` with `BASE_URL=http://localhost:8081` (API must be up). Confirms GET `/health` (200, service=cdss) and GET `/api/v1/patients`. If PostgreSQL is not running, unset `DATABASE_URL` before starting the API to use mock data, or ensure DB has `connect_timeout` (see `src/cdss/db/session.py`) so failed connections fail fast. Full script: `.\scripts\run_phase3_verify.ps1` from repo root.

**Next step: Phase 4 (Safety & Compliance)** — see [§ Phase 4](#phase-4-safety--compliance-priority-3) below.

**Phase 3 verification (this run):**

- **API working:** GET `http://localhost:8081/health` → 200, `{"service":"cdss","status":"ok"}`.
- **Frontend–backend connectivity:** CORS and `VITE_API_URL` are configured; `verify_phase3_connectivity.py` confirms health and (with mock or running DB) GET `/api/v1/patients`. If `DATABASE_URL` points to an unreachable PostgreSQL, restart the API with `DATABASE_URL=""` for mock data, or ensure PostgreSQL is running and reachable.
- **Conclusion:** Phase 3 verified (API up, connectivity in place). Proceed to Phase 4.

### Phase 4: Safety & Compliance (Priority 3)


| Step | Action                                                                                                                                           | Owner      | Verification                                 |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | -------------------------------------------- |
| 4.1  | **Medical audit dashboard**: Implement trace review UI (query AgentEventLog, filter by patient/doctor/time); export for audit                    | Dev        | Auditor can trace a request end-to-end       |
| 4.2  | **RBAC enforcement**: Finalize Cognito (or IdP) groups for Doctor vs Patient; enforce at API Gateway and in backend (reject cross-tenant access) | DevOps/Dev | R1: role-based redirect and access tests     |
| 4.3  | **Audit trails**: Confirm every clinically relevant action writes to RDS with who, what, when, which patient/record                              | Dev        | Audit log coverage review                    |
| 4.4  | **Data localization**: Confirm RDS, S3, and any PII stay in **ap-south-1** (or approved India regions); document in compliance doc               | DevOps     | Architecture review; no PII in other regions |
| 4.5  | **Encryption**: Verify encryption at rest and in transit for all patient data (RDS, S3, API)                                                     | DevOps     | Config review; TLS and KMS in place          |


### Phase 5: Notifications & Alerts (R9)


| Step | Action                                                                                                                                             | Owner | Verification                                        |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------------- |
| 5.1  | **Drug interaction alerts**: When detected, alert prescribing physician/pharmacist before administration (tool or pipeline step)                   | Dev   | Test case: interaction triggers alert and is logged |
| 5.2  | **Emergency protocols**: Define triggers (e.g., vitals thresholds, surgical complication flags) and wire to alert engine and notification channels | Dev   | Runbook + test for one emergency path               |
| 5.3  | **Escalation channels**: Implement multi-channel escalation (e.g., in-app + SMS/email) until acknowledgment; log response times                    | Dev   | R9: escalation and audit trail tests                |
| 5.4  | **Maintenance notifications**: Notify users in advance of maintenance; document alternative access if needed                                       | Ops   | Runbook updated                                     |


### Phase 6: Quality, Performance & Compliance (R10)


| Step | Action                                                                                                                                                                | Owner            | Verification                               |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------ |
| 6.1  | **Property-based / critical-path tests**: Add tests for safety-critical flows (scheduling surgery, drug interactions, emergency alerts) referencing design properties | Dev              | CI runs tests; coverage for critical paths |
| 6.2  | **RBAC boundary tests**: Explicit tests that Patient module cannot access other patients’ data or admin functions                                                     | Dev              | Automated test suite                       |
| 6.3  | **Performance**: Measure and tune so routine queries meet **sub-2-second** target; document bottlenecks                                                               | Dev/Perf         | Load test report                           |
| 6.4  | **Uptime target**: Define SLO (99.5%) and monitoring (alarms, runbooks); deploy in ap-south-1                                                                         | DevOps           | Dashboard and alerting in place            |
| 6.5  | **Regulatory & liability**: Keep doctor-in-the-loop design; maintain docs and audit trails for CDSCO/regulatory submission (see requirements.md Challenges 1–2)       | Legal/Compliance | Checklist and doc ownership                |


### Phase 7: Documentation & Handover


| Step | Action                                                                                                                                                                           | Owner  | Verification                                                 |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------ |
| 7.1  | Keep **PROJECT_REFERENCE.md** as single source for IDs, ARNs, endpoints; update when config changes                                                                              | Dev    | Review on each release                                       |
| 7.2  | Update **api_reference.md** with any new endpoints or MCP contracts; keep **OPENAI_API_ENDPOINTS.md** and **FRONTEND_API_ENDPOINTS.md** in sync with swagger and frontend client | Dev    | All public and AI APIs documented; no undocumented endpoints |
| 7.3  | **Runbooks**: Deploy, scale, incident response, and rollback for AgentCore + Lambda + RDS                                                                                        | DevOps | Ops team sign-off                                            |
| 7.4  | **Onboarding**: New developer can run local API + frontend and execute one full agent flow using PROJECT_STATUS + PROJECT_REFERENCE                                              | Dev    | Onboarding checklist completed                               |


---

## 3.5 Master TODO & Verification Checklist

**How to use:** Work through each phase in order. For every item, perform the **Verify** step and confirm it passes before checking the box. This ensures completed steps are working properly.

### Phase 1: Unblock Core Runtime

- **1.1** Enable Claude 3 Haiku in Bedrock (ap-south-1)  
  - **Verify:** In AWS Console → Bedrock → Model access, confirm Claude 3 Haiku is enabled. Invoke the model (e.g. via AWS CLI or a small script); run a tool-use request and confirm tool calls are returned.
- **1.2** Attach `AmazonBedrockFullAccess` to role `AmazonBedrockAgentCoreSDKRuntime-ap-south-1-6eac3e734d`  
  - **Verify:** Deploy or invoke the AgentCore runtime; run one full agent conversation and confirm no permission errors and response is returned.
- **1.3** Run local API and test agent endpoint  
  - **Verify:** Run `python scripts/run_api_local.py`, then `POST http://localhost:8080/api/v1/agent` with a valid payload (e.g. patient summary request). Confirm 200 response, agent reply in body, and tool results (or tool-invocation evidence) in response/traces.
- **1.4** Deploy Gateway Lambda and register tools with AgentCore  
  - **Verify:** Deploy latest `lambda_handler.py`; in AgentCore config, confirm all 11 tools are registered. Send a request that triggers at least one tool (e.g. get_patient_summary); confirm Lambda is invoked (CloudWatch) and agent response includes real tool output.

**Phase 1 verification scripts (run from repo root):**

- **1.1** From **repo root**: `AWS_REGION=ap-south-1 python scripts/verify_bedrock_haiku_tool_use.py` — Confirms Claude 3 Haiku is enabled and returns tool-use. (PowerShell: `cd D:\AI_Hackathon_CDSS` then `$env:AWS_REGION="ap-south-1"; python scripts/verify_bedrock_haiku_tool_use.py`.)
- **1.2** (Manual) Attach `AmazonBedrockFullAccess` to role `AmazonBedrockAgentCoreSDKRuntime-ap-south-1-6eac3e734d`; run one AgentCore conversation to confirm no permission errors.
- **1.3** Start API: `PYTHONPATH=src python scripts/run_api_local.py`. Then: `PYTHONPATH=src python scripts/verify_phase1_local_api.py` — Or use **PowerShell** (no `&&`): `.\scripts\run_phase1_verify.ps1` from repo root (script sets PYTHONPATH and runs verification; auto-starts server if needed).
- **1.4** Deploy: `cd infrastructure && terraform apply`; register Gateway tools per `docs/agentcore-gateway-manual-steps.md`. The 11 tools in `lambda_handler.py`: `get_hospitals`, `get_ot_status`, `get_abdm_record`, `get_patient`, `list_patients`, `get_surgeries`, `get_surgery`, `get_schedule`, `find_replacement`, `get_medications`, `get_reminders_adherence`. In AgentCore agent config, confirm all 11 are registered; send a request that triggers one (e.g. patient summary), then check CloudWatch for Lambda invocations and that the agent response includes real tool output.

**Troubleshooting (are these “errors” fixed?):**


| Issue                                | Fixed in code?                                                                                                            | What you still do                                                                                                            |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Phase 1.3 → 404**                  | Yes. Router now serves GET `/health` and `/` with 200 + `service: cdss`. Verification script can detect the right server. | If something else is on 8080, stop it or use `$env:PORT="8081"; $env:BASE_URL="http://localhost:8081"` and run verify again. |
| **PowerShell `&&` error**            | Yes. Use `;` in one-liners or run `**.\scripts\run_phase1_verify.ps1`** from repo root (no `&&`).                         | Run from repo root so the script finds `src` and `scripts`.                                                                  |
| **Bedrock “model not available”**    | Yes. Code defaults to **Nova Lite** (`apac.amazon.nova-lite-v1:0`); Converse API used for Nova.                           | In AWS Console → Bedrock (ap-south-1) → Model access, enable **Amazon Nova Lite** (or Claude 3 Haiku).                       |
| **Swagger UI “Failed to load spec”** | Yes. `run_api_local.py` sets `CDSS_REPO_ROOT`; router’s `_repo_root()` uses it to serve `docs/swagger.yaml`.              | Start the API from repo root (`python scripts/run_api_local.py`) so `docs/swagger.yaml` exists relative to repo.             |


### Phase 2: Real Integrations

- **2.1** Define MCP contract for hospital HIS and ABDM  
  - **Verify:** Document exists in api_reference.md or design.md with endpoints, auth, and payloads for each system.
- **2.2** Implement MCP clients/servers for real hospital/ABDM (replace stubs)  
  - **Verify:** Unit or integration tests pass against mock or sandbox; no stub-only path in production code for new integrations.
- **2.3** Wire Patient Agent to real ABDM (or sandbox)  
  - **Verify:** In test env, request patient summary for a known ABDM id; response includes data from ABDM (or sandbox) and not only static stub.
- **2.4** Wire Resource/Scheduling to real or simulated OT/staff/equipment  
  - **Verify:** Availability or conflict check returns results from live (or simulated) data source; logs show correct data source.
- **2.5** All external URLs/credentials from Secrets Manager or IAM only  
  - **Verify:** Grep/code review finds no hardcoded secrets or .env used for production; Secrets Manager keys documented.

### Phase 2B: Backend API Integration

- **2B.1** Repository analysis: frontend usage, backend routes, DB schema, docs (FRONTEND_API_ENDPOINTS.md, OPENAI_API_ENDPOINTS.md, DEVELOPMENT_COMPLETION_STEPS.md)  
  - **Verify:** Written summary of gaps (missing routes, controllers, or DB ops for frontend-called endpoints); references to handler files and frontend client.
- **2B.2** Generate `/docs/swagger.yaml` (OpenAPI 3.x): auth, patient, doctor, surgery, resource, scheduling, conversation, AI APIs  
  - **Verify:** File exists; every endpoint in [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md) summary table is in swagger with request/response schemas; no schema errors when validated (e.g. openapi-spec-validator).
- **2B.3** Verify backend per endpoint: controller exists, DB ops, request validation, response schema matches frontend  
  - **Verify:** For each swagger path, a handler exists in `src/cdss/api/handlers/*`; validation present; response shape matches what doctor-dashboard `client.js` expects (or doc updated).
- **2B.4** AI integration: Bedrock/OpenAI wrappers at `/api/ai/*` for summarization, entity extraction, surgery support, translation  
  - **Verify:** Call each of `/api/ai/summarize`, `/api/ai/entities`, `/api/ai/surgery-support`, `/api/ai/translate` (or equivalent); 200 and validated JSON; no raw model output without schema.
- **2B.5** Generate missing: routes, controllers, migrations, models, validations  
  - **Verify:** No 404 for any endpoint in FRONTEND_API_ENDPOINTS.md or swagger; new tables/columns have migrations and are applied.
- **2B.6** Swagger UI at `/api/docs` with swagger-ui, OpenAPI validation, API testing  
  - **Verify:** Open `GET /api/docs` in browser; Swagger UI loads; Try-it-out for at least one endpoint succeeds against running API.
- **2B.7** Update OPENAI_API_ENDPOINTS.md, FRONTEND_API_ENDPOINTS.md, DEVELOPMENT_COMPLETION_STEPS.md when endpoints change  
  - **Verify:** OPENAI_API_ENDPOINTS.md exists and lists AI endpoints; FRONTEND_API_ENDPOINTS.md and DEVELOPMENT_COMPLETION_STEPS.md reflect current API surface.
- **2B.8** Output: created endpoints, updated schema summary, swagger file path, missing integrations report
  - **Verify:** Document or PR contains the four artifacts; missing integrations (if any) are listed with recommended actions.

**Phase 2B completion (verified):**


| Step | Status | Evidence                                                                                                                                                                         |
| ---- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2B.1 | ✅ Done | FRONTEND_API_ENDPOINTS.md and handlers aligned; no missing frontend-called routes                                                                                                |
| 2B.2 | ✅ Done | `docs/swagger.yaml` exists; all summary-table endpoints + AI APIs documented with request/response schemas                                                                       |
| 2B.3 | ✅ Done | Router dispatches every path to a handler in `src/cdss/api/handlers/*` (patient, admin, surgery, resource, engagement, scheduling, activity, hospitals, ai, supervisor)          |
| 2B.4 | ✅ Done | `src/cdss/api/handlers/ai.py`: POST `/api/ai/summarize`, `/api/ai/entities`, `/api/ai/surgery-support`, `/api/ai/translate`; validated JSON with `safety_disclaimer`             |
| 2B.5 | ✅ Done | No 404 for any endpoint in FRONTEND_API_ENDPOINTS or swagger; no new DB migrations required for Phase 2B                                                                         |
| 2B.6 | ✅ Done | GET `/api/docs` serves Swagger UI (router `proxy == "docs"`); GET `/docs/swagger.yaml` serves OpenAPI spec                                                                       |
| 2B.7 | ✅ Done | OPENAI_API_ENDPOINTS.md exists and lists AI endpoints; FRONTEND_API_ENDPOINTS.md and DEVELOPMENT_COMPLETION_STEPS.md updated                                                     |
| 2B.8 | ✅ Done | **Created endpoints:** all in swagger + `/api/ai/*`. **Schema summary:** no DB schema change in Phase 2B. **Swagger path:** `docs/swagger.yaml`. **Missing integrations:** none. |


**Phase 2B build output (current):** Created endpoints: `/api/ai/summarize`, `/api/ai/entities`, `/api/ai/surgery-support`, `/api/ai/translate`; GET `/api/docs` (Swagger UI); GET `/docs/swagger.yaml`. Swagger file: `docs/swagger.yaml`. See `OPENAI_API_ENDPOINTS.md`. Config: `config.json`, `all-secrets.json`, `config/gateway-config.schema.json`; Bedrock defaults to Nova Lite when Haiku not enabled.

### Phase 3: Frontend & UX

- **3.1** Frontend points to AgentCore API; CORS and auth work  
  - **Verify:** From browser at localhost:5173, trigger a request to the API; response displayed without CORS errors; auth headers sent if required.
- **3.2** Doctor Module: list patients, trigger flows, show summaries and audit context  
  - **Verify:** Manually test: list patients, run Patient/Surgery/Resource/Scheduling flows, see summaries and audit info; matches R1–R5 acceptance criteria.
- **3.3** Patient Module restricted to single Patient_ID  
  - **Verify:** Log in as patient; confirm only own history/reminders/summary visible; attempt to access another patient ID returns 403 or equivalent.
- **3.4** Multilingual: Hindi + one regional language and terminology  
  - **Verify:** Request response in Hindi (and one other language); check terminology list is used; R7 acceptance criteria met.

**Phase 3.4 (completed):** Backend: `cdss.services.i18n` with `APPROVED_TERMINOLOGY` (Hindi, Tamil); `get_approved_terminology_for_lang()` used in `/api/ai/translate`; GET `/api/v1/terminology` returns approved terms; supervisor translates agent reply when `Accept-Language: hi` or `?lang=ta`. UI: PatientConsultation `summaryLangLabels`, Settings language option. See [docs/TERMINOLOGY.md](TERMINOLOGY.md).
- **3.5** Safety disclaimers on all patient-facing AI content  
  - **Verify:** Review checklist: summaries and educational content include required disclaimer; no unbranded medical advice.

**Phase 3 verification (codebase check):**


| Step | Status     | Evidence                                                                                                                                                                                                                                                                                  |
| ---- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.1  | ✅ Done     | `config.js`: `VITE_API_URL`, `VITE_USE_MOCK`; `client.js` uses `config.apiUrl`, sends `Authorization: Bearer` when `getToken` set. `common.py`: `cors_headers()`; router and `run_api_local.py` send CORS. AIChat calls `postAgent('/agent')` and displays `reply` + `safety_disclaimer`. |
| 3.2  | ✅ Done     | `client.js`: `getPatients`, `getPatient`, `getDashboard`, `postAgent`, `getSurgeries`, `getResources`, `getSchedule`, consultations, admin/audit. FRONTEND_API_ENDPOINTS: Patients, Surgery, Resources, Schedule, AIChat, PatientConsultation, Medications, Admin*.                       |
| 3.3  | ✅ Done     | `router.py`: for `role == "patient"` blocks GET `/api/v1/patients` (list) with 403; for `/api/v1/patients/:id` enforces `patient_id_in_path == _get_patient_id(claims)` else 403 "Patients may only access their own record."                                                             |
| 3.4  | ✅ Done     | Backend: `i18n.APPROVED_TERMINOLOGY` (Hindi, Tamil); `get_approved_terminology_for_lang()` in `/api/ai/translate`; GET `/api/v1/terminology`; supervisor translates reply per Accept-Language/lang. UI: summaryLangLabels, Settings. See [TERMINOLOGY.md](TERMINOLOGY.md). |
| 3.5  | ✅ Done     | AIChat shows `safety_disclaimer` in `ai-message__disclaimer`; router/supervisor/bedrock chat and `/api/ai/*` handlers return `safety_disclaimer`; Lambda and swagger include it.                                                                                                          |


**Phase 3 run (executed):** Local API on port 8081; `scripts/verify_phase1_local_api.py` with `BASE_URL=http://localhost:8081` — **PASS**. Agent endpoint returned 200, intent `patient`, agent `patient_agent`, reply with patient list, `safety_disclaimer` present.

### Phase 4: Safety & Compliance — **Next step**

- **4.1** Medical audit dashboard: trace review UI  
  - **Verify:** Open dashboard; filter by patient/doctor/time; select one request and trace end-to-end; export works for audit.
- **4.2** RBAC: Cognito groups and enforcement at API and backend  
  - **Verify:** Doctor and Patient roles in Cognito; API rejects cross-tenant access; automated R1 role-based tests pass.
- **4.3** Every clinically relevant action written to RDS audit  
  - **Verify:** Audit log coverage review: key actions (e.g. view patient, create surgery, send reminder) have who/what/when/patient or record.
- **4.4** Data localization: RDS/S3/PII in ap-south-1 (or approved India regions)  
  - **Verify:** Architecture review; no PII stored or processed outside approved regions; documented in compliance doc.
- **4.5** Encryption at rest and in transit for patient data  
  - **Verify:** RDS, S3, and API config show TLS and encryption (e.g. KMS); config review signed off.

**Phase 4 – AI summary and AI chatbot check (prerequisite for safety/compliance):**

Before full Phase 4 (audit dashboard, RBAC, etc.), verify that **AI summary** and **AI chatbot** work:


| Check                       | Endpoint                           | Verification                                                                                                                                                                                                                                          |
| --------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI chatbot**              | POST `/agent`                      | AIChat page sends message; response has `data.reply` and `safety_disclaimer`. Supervisor routes to Patient/Surgery/Resource/Scheduling/Engagement agents or Bedrock chat.                                                                             |
| **AI summary**              | POST `/api/ai/summarize`           | Request body `{ "text": "..." }` or `{ "conversation": [...] }`; response has `summary` and `safety_disclaimer`.                                                                                                                                      |
| **Consultation AI summary** | POST `/api/v1/consultations/start` | When starting a consultation (patient_id, doctor_id), response includes `summary` and `ai_summary` (Bedrock-generated from patient + recent visits when configured). PatientConsultation page shows this in the "AI summary & recommendations" block. |


**Run Phase 4 AI verification:** From repo root, start the API (`python scripts/run_api_local.py`), then:

- **PowerShell:** `.\scripts\run_phase4_verify.ps1` (uses BASE_URL=[http://localhost:8081](http://localhost:8081) if not set)
- **Or:** `BASE_URL=http://localhost:8081 python scripts/verify_phase4_ai.py`

Script checks: GET `/health`, POST `/agent` (AI chatbot), POST `/api/ai/summarize` (AI summary). All must return 200 with expected fields. For consultation start to return a non-empty summary, Bedrock must be configured (`BEDROCK_CONFIG_SECRET_NAME` or config.json) and the patient must exist in the DB.

**Real database verification (Aurora):** When the dashboard and API are connected to Aurora, run verification against the real DB (no mock):

1. Start the API with `DATABASE_URL` set (and SSM tunnel if Aurora is in a VPC). Ensure GET `/health` returns `"database": "connected"`.
2. Run **Phases 1–4 with real DB:**  
   - **PowerShell:** `.\scripts\run_phases_1_to_4_verify.ps1`  
   - **Or:** `BASE_URL=http://localhost:8080 python scripts/verify_phases_1_to_4_real_db.py`  
   The script requires `database: connected`, 200 from GET `/api/v1/patients`, POST `/agent`, POST `/api/ai/summarize`, and GET `/api/v1/terminology`. Use `REAL_DB=0` to skip the database requirement and still run the other checks.
3. **Phase 3 only (real DB):** `REAL_DB=1 BASE_URL=http://localhost:8080 python scripts/verify_phase3_connectivity.py` — fails if `/health` does not have `database: connected` or if GET `/api/v1/patients` returns 500.

### Phase 5: Notifications & Alerts

- **5.1** Drug interaction alerts to physician/pharmacist before administration  
  - **Verify:** Test case: trigger interaction scenario; alert created and logged; recipient (or mock) receives notification.
- **5.2** Emergency protocols: triggers and wiring to alert engine  
  - **Verify:** Runbook lists triggers; at least one emergency path (e.g. vitals threshold) wired and tested.
- **5.3** Multi-channel escalation until acknowledgment; response times logged  
  - **Verify:** Test escalation path; confirm multiple channels and audit trail with response times (R9).
- **5.4** Maintenance notifications and alternative access  
  - **Verify:** Runbook includes how to notify users and alternative access; Ops sign-off.

### Phase 6: Quality, Performance & Compliance

- **6.1** Property-based / critical-path tests for safety-critical flows  
  - **Verify:** CI runs tests; scheduling surgery, drug interactions, emergency alerts covered; design properties referenced.
- **6.2** RBAC boundary tests: Patient cannot access others’ data or admin  
  - **Verify:** Automated test suite includes these cases and passes.
- **6.3** Routine queries meet sub-2-second target; bottlenecks documented  
  - **Verify:** Load test report shows latency and any tuning done.
- **6.4** SLO 99.5% and monitoring (alarms, runbooks) in ap-south-1  
  - **Verify:** Dashboard and alarms exist; runbooks updated; on-call can follow.
- **6.5** Regulatory: doctor-in-the-loop, docs and audit for CDSCO  
  - **Verify:** Checklist and doc ownership confirmed; no AI-only decisions.

### Phase 7: Documentation & Handover

- **7.1** PROJECT_REFERENCE.md is single source for IDs, ARNs, endpoints  
  - **Verify:** Spot-check on release: all referenced IDs/ARNs/endpoints match PROJECT_REFERENCE.md.
- **7.2** api_reference.md includes all public endpoints and MCP contracts; OPENAI_API_ENDPOINTS.md and FRONTEND_API_ENDPOINTS.md match swagger and client  
  - **Verify:** Every public API and MCP contract has an entry; AI endpoints in OPENAI_API_ENDPOINTS.md; frontend endpoints in FRONTEND_API_ENDPOINTS.md match client.js and swagger.
- **7.3** Runbooks for deploy, scale, incident, rollback (AgentCore, Lambda, RDS)  
  - **Verify:** Ops team runs through runbooks and signs off.
- **7.4** Onboarding: new dev runs local API + frontend and one full agent flow  
  - **Verify:** New developer follows PROJECT_STATUS + PROJECT_REFERENCE and completes onboarding checklist.

---

## 4. Critical Implementation Challenges (from requirements.md)

- **Regulatory (CDSCO/SaMD)**: Proceed in parallel; start with non-diagnostic features; keep full audit and docs.
- **Medical liability**: Strict doctor-in-the-loop; all recommendations logged; disclaimers on patient-facing content.
- **Data privacy**: Encryption, India data localization, consent management—already reflected in Phase 4 and 6.
- **Doctor adoption**: Gradual rollout, training, feedback loops; AI as augmentation only.
- **Real-time sync**: Reliable status updates (Resource/Scheduling); fallbacks and manual override paths.
- **Government competition**: Differentiate on multi-agent design and advanced features; consider partnerships.

---

## 5. Success Criteria for “Project Complete”

Track detailed progress in **[§3.5 Master TODO & Verification Checklist](#35-master-todo--verification-checklist)**; the list below is the phase-level gate.

- All **Phase 1** steps done (and verified): Bedrock model + IAM working; local and deployed agent runs with real tools.
- **Phase 2** (real MCP/ABDM) either fully wired or clearly scoped and scheduled with no blocking stubs in production path.
- **Phase 2B**: Backend API integration complete: `/docs/swagger.yaml` generated, `/api/docs` serving Swagger UI, `/api/ai/*` implemented, all frontend-called endpoints have backend implementation; OPENAI_API_ENDPOINTS.md and FRONTEND_API_ENDPOINTS.md updated.
- **Phase 3**: Frontend connected; Doctor and Patient modules meet R1; multilingual baseline and disclaimers in place. **Phase 3 run verified** (local API + agent endpoint; see Phase 3 run above).
- **Phase 4**: Audit dashboard live; RBAC enforced; audit trails and data localization verified. **← Next step.**
- **Phase 5**: At least one end-to-end notification/alert path (e.g., drug interaction) implemented and tested.
- **Phase 6**: Critical-path and RBAC tests in CI; performance and uptime targets documented and monitored.
- **Phase 7**: Reference docs and runbooks updated; one successful onboarding run.

---

## 6. Quick Reference

- **Local API**: `python scripts/run_api_local.py` → `http://localhost:8080` (or set `PORT=8081` and use `http://localhost:8081` if 8080 is in use)
- **Agent endpoint**: `POST /api/v1/agent` or `POST /agent`
- **Health**: `GET /health`
- **Swagger UI**: `GET /api/docs` (when Phase 2B is done)
- **AI APIs**: `/api/ai/*` (summarize, entities, surgery-support, translate) — see OPENAI_API_ENDPOINTS.md when created
- **Phase 4 AI check**: `.\scripts\run_phase4_verify.ps1` or `BASE_URL=http://localhost:8081 python scripts/verify_phase4_ai.py` (AI chatbot + AI summary)
- **Phases 1–4 real DB**: `.\scripts\run_phases_1_to_4_verify.ps1` or `python scripts/verify_phases_1_to_4_real_db.py` (requires DATABASE_URL; API must return database=connected)
- **Key code**: `agentcore/agent/cdssagent/src/main.py`, `infrastructure/gateway_tools_src/lambda_handler.py`, `src/cdss/api/handlers/*`
- **Config**: [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) (ARNs, secrets, region)
- **Frontend API usage**: [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md)
- **API contract**: `/docs/swagger.yaml` (to be generated in Phase 2B)

---

## 7. End of development: MCP / ABDM config (do last)

When you are ready to wire **real Hospital HIS** and **ABDM** (or sandbox), set the following. Skip until then; stubs work without them.

- **Local runs:** In `**config.json`** set `mcp_hospital_endpoint`, `mcp_abdm_endpoint`, and/or `abdm_sandbox_url` to your base URLs (or set env vars `MCP_HOSPITAL_ENDPOINT`, `MCP_ABDM_ENDPOINT`, `ABDM_SANDBOX_URL`). See `**.env.example**` for the list.
- **AWS (Lambda / AgentCore):** Put the same keys (and optional `hospital_mcp_api_key`, `abdm_sandbox_api_key`) in the **app-config** secret in Secrets Manager. Use `**docs/app-config-example.json`** as the structure.
- **Contract and keys:** [MCP_CONTRACTS.md](MCP_CONTRACTS.md) documents endpoints, auth, and required secret keys.

---

> **Safety disclaimer**: This system is for decision support only. All medical decisions require the judgment of a qualified clinician.

