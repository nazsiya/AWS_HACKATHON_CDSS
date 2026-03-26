# AI Assistant Debug Log (This Conversation) — 2026-03-25

## Goal

Debug why the deployed CDSS “AI Assistant” was not generating the expected outputs (notes summary truncation/blank responses and missing tool results like drug interactions, prescription drafts, lab test suggestions, and pre-op assessment).

## Issues Solved (and How)

### 1) Notes summary was truncated with ellipsis (`…`) and not complete

**Symptom**

- Patient notes summary ended early (ex: “That’s completely unders…”).

**Root cause**

- The live endpoint `POST /api/v1/ai/summarize` was implemented as a **hardcoded stub** in `backend/api/rest/database_crud.py`.
- It returned `first ~220 chars + …` instead of calling the real AI summarization logic.

**Fix**

- Replaced the stub handler in `backend/api/rest/database_crud.py` for:
  - `resource in ['/ai/summarize', '/api/ai/summarize']`
- New behavior:
  - Attempt Bedrock/Nova summarization using `backend/agents/shared/BedrockClient`.
  - If the model output looks like echo/truncation, switch to a deterministic **rule-based summary** so the UI always shows a usable summary.

**Validated**

- `POST /api/v1/ai/summarize` now returns a full bullet summary for the same notes payload (no more `Summary of notes: first N chars…`).

### 2) “Internal server error” (502) after a manual Lambda update

**Symptom**

- UI showed “Internal server error”.
- API Gateway routes returned `502 Bad Gateway`.

**Root cause**

- `DashboardFunction` was overwritten with an **incomplete deployment zip** during a manual update.
- The zip only included `backend/api/rest/`*, so imports from `src/cdss/`* and/or runtime dependencies broke, causing the Lambda to fail and API Gateway to return `502`.

**Fix**

- Restored the correct bundle by running the proper CDK deployment:
  - `npx cdk deploy CdssStack --app "npx ts-node bin/cdss.ts" --context EnvName=prod`

**Validated**

- `GET /health` returns `200`.
- `GET /api/v1/patients` returns `200`.
- `POST /api/v1/ai/summarize` returns `200` with bullet summaries.

### 3) AI Assistant routing intermittently returned only “Routing request …” / missing results

**Symptom**

- In AI Assistant, some flows like drug interactions / prescription / lab tests / pre-op assessment were missing or only showed routing text.

**Root cause (pre-op assessment specifically)**

- `SurgeryPlanningAgent` could not publish to the EventBridge bus due to missing `events:PutEvents` permission.
- When sync pre-op generation depended on that flow, the call failed and the Supervisor fell back to showing only the routing line.

**Fix**

- Updated CDK to allow EventBridge publishing from relevant sub-agents in `infra/lib/cdss-stack.ts`:
  - Added `eventBus.grantPutEventsTo(patientAgent)`
  - Added `eventBus.grantPutEventsTo(surgeryAgent)`

**Root cause (prescription/drug interactions routing)**

- Supervisor routing prompt/tool descriptions were not explicit enough that those intents map to `PatientAgent` tools.
- Bedrock therefore returned “tool not supported” style responses.

**Fix**

- Updated routing/tool descriptions and system prompts so Bedrock routes:
  - Drug interactions → `PatientAgent` tool `check_drug_interactions`
  - Prescription draft → `PatientAgent` tool `generate_prescription`
  - Lab tests → `PatientAgent` tool `suggest_lab_tests`
  - Treatment plan → `PatientAgent` tool `get_treatment_plan`
- Changes made in:
  - `backend/agents/shared/config.py` (extended `SYSTEM_PROMPTS` and described capabilities)
  - `backend/agents/supervisor/handler.py` (updated `route_to_patient_agent` tool description)

**Validated (backend)**

- Direct `/agent` calls with an explicit `patient_id` show the expected outputs:
  - “Check drug interactions” returns interaction text
  - “Generate prescription” returns prescription draft text
  - “Suggest lab tests” returns lab list text
  - “Pre-op assessment” returns checklist text (not only routing text)

### 4) Frontend summary display / parsing issues (earlier in the project)

**Fixes already applied earlier**

- `frontend/apps/doctor-dashboard/src/pages/AIChat/AIChat.jsx` and `frontend/apps/doctor-dashboard/src/api/client.js`
  - Added robust extraction/unwrapping of Lambda response payloads.
  - Stripped model `<thinking>...</thinking>` blocks.
  - Ensured the UI displays the correct assistant content.

## What’s Next (Remaining Work)

### A) Make AI Assistant UX reliable (UI should always send `patient_id` + keep intent stable)

Right now, `AIChat.jsx` sends:

- `postAgent({ message: msg, history: messages })`

It does NOT reliably pass `patient_id` separately.
That means:

- If the user sends only `PT-1018`, the Supervisor may not interpret intent correctly.
- Tool routing can degrade (even with backend fixes), leading to missing/ask-for-context behavior.

**Next required change**

- Update `frontend/apps/doctor-dashboard/src/pages/AIChat/AIChat.jsx` to:
  - Detect `PT-xxxx` in the message (or store it when the user selects it).
  - Send `patient_id` explicitly in the `/agent` request payload.
  - Optionally preserve `session_id` across turns (so routing context is stable).

### B) Add an automated “AI Assistant intent” regression test

Create a simple test script that:

1. Calls `/agent` with `patient_id: PT-1018` and messages:
  - “Check drug interactions”
  - “Generate prescription”
  - “Suggest lab tests”
  - “Pre-op assessment”
2. Asserts the response contains expected keywords (or tool output patterns) and does not contain “Routing request…” only.

## Files Touched (High Signal)

- `backend/api/rest/database_crud.py` (replace summarize stub + rule-based fallback)
- `infra/lib/cdss-stack.ts` (grant EventBridge `PutEvents` to patient/surgery agents)
- `backend/agents/shared/config.py` (expand Supervisor/Patient tool routing capability prompts)
- `backend/agents/supervisor/handler.py` (improve routing tool description)
- (Earlier work) `frontend/apps/doctor-dashboard/src/pages/AIChat/AIChat.jsx`, `frontend/apps/doctor-dashboard/src/api/client.js`

