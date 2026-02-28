# CDSS — Design & Implementation

This document describes design decisions and a step-by-step implementation guide for the Clinical Decision Support System (CDSS) multi-agent platform.

---

## 1. Design principles

- **Serverless-first**: Lambda, API Gateway, DynamoDB, S3, EventBridge to keep cost predictable and operations minimal.
- **DISHA compliance**: Audit logs for all access and decisions; PHI masking in logs; consent and ABDM alignment where applicable.
- **Multi-agent orchestration**: A single Supervisor routes intents to specialized agents (Patient, Surgery, Resource, Scheduling, Engagement) and aggregates responses.
- **Budget**: Target <$100/month — use on-demand DynamoDB, single-AZ RDS if needed, minimal OpenSearch, and Bedrock usage controls.

---

## 2. Architecture summary

- **Frontend**: React (Doctor Dashboard, Surgery Planning), React Native (Patient App), Amplify for hosting; Cognito + JWT for auth; Transcribe for voice; Translate for Hindi/Tamil/Telugu/Bengali.
- **API layer**: REST and WebSocket via API Gateway; optional ECS Fargate for real-time surgical WebSocket if needed.
- **Agent layer**: Python 3.12 Lambdas; one **router** Lambda receives all REST requests and dispatches by path to the correct agent handler; each agent uses Bedrock (Claude 3 Haiku) and optional tool use.
- **Data**: DynamoDB (sessions, medication schedules), S3 (documents, knowledge corpus), RDS PostgreSQL (patient/consultation records if required), OpenSearch (RAG over patient history).
- **Async**: EventBridge for inter-agent events and audit; SQS DLQ for retries; SNS Pinpoint for reminders; SES for doctor escalation.
- **MCP**: Clinical Protocols (drug interactions, evidence), Hospital Systems (OT status, beds), ABDM/EHR, Telemedicine (specialist escalation).

---

## 3. Implementation steps

### Phase 1 — Foundation

1. **Repo and structure**  
   Use the provided layout: `src/cdss/{api,agents,core,models,services}`, `infrastructure/`, `tests/`, `docs/`.

2. **Core and config**  
   - Implement `core/config.py` (env-based).  
   - Implement `core/bedrock_client.py`: get Bedrock Runtime client; add `invoke_converse()` (or InvokeModel) with system prompt and user message.  
   - Implement `core/logging.py` (structured logs for CloudWatch).  
   - Implement `core/disha.py`: `audit_log()` to CloudWatch (and optionally EventBridge); `mask_phi()` for any PHI in logs.

3. **Base agent**  
   - In `agents/base.py`, keep `get_tools()` and `get_system_prompt()` abstract; in `invoke()`, call Bedrock (e.g. Converse API) with system prompt and user message.  
   - Add optional tool-use loop: if Bedrock returns tool calls, execute them (e.g. call RAG, MCP, DynamoDB) and send results back until final response.

### Phase 2 — Agents

4. **Supervisor**  
   - `route_intent()`: use keyword/heuristic or a small Bedrock call to map intent to one of the five agents.  
   - `aggregate_response()`: merge sub-agent responses (e.g. concatenate or summarize via Bedrock).

5. **Patient Agent**  
   - Wire `get_history` to RDS or DynamoDB; `get_rag_summary` to OpenSearch (embed query, search patient history index, return top-k chunks + optional Bedrock summary).  
   - `create_patient` / `update_record`: write to RDS or DynamoDB; call `audit_log()`.  
   - Use Comprehend Medical in pipeline for NER if you need to extract entities from notes before storing or searching.

6. **Surgery Planning Agent**  
   - `get_protocols` / `get_ot_checklists`: call Clinical Protocols MCP and/or local data.  
   - `analyse_surgery`: send plan + protocol context to Bedrock; return structured analysis.  
   - `generate_checklist`: combine protocol + plan via Bedrock; return checklist (e.g. list of steps).

7. **Resource Agent**  
   - `get_ot_availability` / `check_ot`: call Hospital Systems MCP (or stub).  
   - `get_equipment` / `allocate_equipment`: read/write DynamoDB or MCP.

8. **Scheduling Agent**  
   - `get_appointments` / `book_slot` / `book_ot` / `resolve_conflict`: persist in DynamoDB; publish events to EventBridge for reminders or conflict resolution.

9. **Engagement Agent**  
   - `send_reminder`: call Pinpoint (SMS/push); use Translate for language.  
   - `escalate_to_doctor`: send email via SES and/or Telemedicine MCP.

### Phase 3 — API and infra

10. **API Gateway + Lambda**  
    - Keep single router Lambda: parse path, dispatch to the right handler (supervisor, patient, surgery, resource, scheduling, engagement).  
    - Add middleware: CORS, request ID logging, optional JWT validation (Cognito).  
    - Terraform: API Gateway REST (and optionally WebSocket); one integration to the router Lambda; deploy.

11. **Terraform modules**  
    - **Lambda**: zip from `src/`, handler map including `api` → router; IAM for Bedrock, DynamoDB, S3, EventBridge, Pinpoint, SES, Comprehend Medical, Transcribe, Translate.  
    - **DynamoDB**: sessions table (sessionId, sk), medication_schedules (patientId, scheduleId); on-demand.  
    - **S3**: buckets for documents and knowledge corpus; encryption (AES-256).  
    - **EventBridge**: bus for CDSS events; optional rules to trigger Engagement or other Lambdas.  
    - **OpenSearch** (optional): small domain for RAG; index patient history embeddings; secure access from Lambda.

12. **Secrets and env**  
    - Store DB credentials and API keys in Secrets Manager; reference in Lambda env or via SDK.  
    - Set `OPENSEARCH_ENDPOINT`, `DYNAMODB_*`, `S3_*`, `EVENT_BUS_NAME`, `PINPOINT_APP_ID`, `DISHA_AUDIT_LOG_GROUP` in Lambda.

### Phase 4 — RAG and MCP

13. **RAG pipeline**  
    - Ingest: medical documents and consultation text → chunk → embed (Bedrock Embeddings or compatible model) → index in OpenSearch.  
    - Query: embed user question, search OpenSearch, pass chunks to Bedrock for answer; cite sources.

14. **MCP integrations**  
    - Implement adapters in `services/mcp/` that call external MCP servers or REST APIs.  
    - Map agent tools to these adapters (e.g. Surgery Agent → Clinical Protocols MCP; Resource Agent → Hospital Systems MCP).

### Phase 5 — Frontend and E2E

15. **Amplify + React**  
    - Doctor Dashboard and Surgery Planning UI: call API Gateway with JWT (Cognito).  
    - Patient App: React Native; same API; Pinpoint for push.

16. **E2E tests**  
    - Use API Gateway URL and test critical flows: route intent → agent response, book slot, send reminder (mock Pinpoint if needed).

---

## 4. Key files reference

| Area | Path | Purpose |
|------|------|--------|
| Router | `src/cdss/api/handlers/router.py` | Path-based dispatch to agent handlers |
| Supervisor | `src/cdss/agents/supervisor.py` | route_intent, aggregate_response |
| Agents | `src/cdss/agents/*_agent.py` | Domain logic and Bedrock invocation |
| Config | `src/cdss/core/config.py` | Env-based settings |
| Bedrock | `src/cdss/core/bedrock_client.py` | Converse/InvokeModel |
| DISHA | `src/cdss/core/disha.py` | Audit log, PHI masking |
| RAG | `src/cdss/services/rag.py` | OpenSearch search |
| MCP | `src/cdss/services/mcp/*.py` | External protocol and hospital integrations |
| Infra | `infrastructure/*.tf`, `modules/*` | Lambda, API Gateway, DynamoDB, S3, EventBridge |

---

## 5. Security and compliance checklist

- [ ] All PHI in logs masked via `mask_phi()`; no raw PII in CloudWatch.  
- [ ] DISHA audit events for create/update/access of patient and consultation data.  
- [ ] Lambda in VPC if talking to RDS/OpenSearch; minimal IAM per function.  
- [ ] API Gateway: use Cognito authorizer and/or API keys for production.  
- [ ] Secrets in Secrets Manager; rotate DB and third-party keys periodically.  
- [ ] S3 and DynamoDB encryption at rest; TLS in transit.

---

## 6. Cost levers

- **Bedrock**: Control max tokens and cache system prompts where supported; use Haiku for most tasks.  
- **DynamoDB**: On-demand; add TTL for session data to avoid unbounded growth.  
- **OpenSearch**: Small instance or serverless; limit index size.  
- **Lambda**: Tune memory and timeout; reuse connections (e.g. Bedrock, DB) across invocations.  
- **Pinpoint/SES**: Set limits and monitor usage.

This design and implementation guide should be read together with [docs/architecture.md](docs/architecture.md) and [docs/deployment.md](docs/deployment.md).
