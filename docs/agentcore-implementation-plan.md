# AgentCore Implementation Plan

**Purpose:** Migrate the CDSS AI layer to **Amazon Bedrock AgentCore** for MCP integration, observability, memory, and production readiness — aligning with [requirements.md](./requirements.md) (Req 8 MCP, Req 10 audit/Bedrock) and [.cursor/rules/CDSS.mdc](../.cursor/rules/CDSS.mdc) (clinical schemas, trace review, safety).

> **References:** [Implementation Plan](./implementation-plan.md) | [Requirements](./requirements.md) | [CDSS.mdc](../.cursor/rules/CDSS.mdc) | [AgentCore Docs](https://docs.aws.amazon.com/bedrock-agentcore/?region=us-east-1)

---

## Alignment with CDSS and Requirements

| Source | Alignment |
|--------|-----------|
| **requirements.md** | Req 8: MCP for agent-to-agent communication; event logs and audit. Req 10: AWS Bedrock, MCP servers, audit trails, RBAC, data localization (India). Req 2–7: Patient_Agent, Surgery_Agent, Resource_Agent, Scheduling_Agent, Patient_Engagement_Agent. |
| **CDSS.mdc** | Clinical assessment schemas (priority, confidence, risk_factors); surgery readiness (pre_op_status, checklist_flags, requires_senior_review); trace review and medical audit; safety disclaimers and senior review flags. |
| **CDSS product** | Staff app (Doctor_Module) + Patient portal (Patient_Module); `/api/v1/*` REST API; multi-agent Lambda router. AgentCore will host or back the same agents (Patient, Surgery, Resource, Scheduling, Engagement) with Gateway-exposed MCP tools. There is NO Triage agent. |

**Region:** Data residency per requirements is India (ap-south-1). Use AgentCore in regions where available; keep persistence and PII in ap-south-1 where required.

---

## Agreed Approach (Feb 2026)

| Topic | Decision |
|-------|----------|
| **Experience** | No prior AgentCore use; Console access available |
| **AC-1 scope** | Single CDSS AgentCore runtime + Gateway PoC; migrate severity assessment, routing, and other CDSS agents (Patient, Surgery, Resource, Scheduling, Engagement) once the pattern is proven. |
| **Gateway data** | Try MCP for hospital knowledge if available; otherwise synthetic/stub data (aligned with CDSS MCP adapter in implementation-plan). |
| **IaC** | Terraform if not too time-consuming; otherwise Console |
| **Cutover** | Converse/current Lambda fallback during migration; switch fully once AgentCore path is stable |
| **Hospital data** | No MCP server for hackathon; synthetic/stub data is acceptable |
| **AC-1 observability** | Include basic tracing/metrics; satisfy CDSS.mdc trace review and medical audit (Req 10 audit trails) |

---

## Why AgentCore

| Need | Current (Converse/Classic Agents) | AgentCore |
|------|----------------------------------|-----------|
| Hospital / resource data (MCP) | Manual integration, stubs (cdss.mcp.adapter) | **Gateway** – expose MCP tools natively (Req 8) |
| Trace review / medical audit | Custom logging | **Observability** – tracing, OpenTelemetry, CloudWatch (CDSS.mdc; Req 10) |
| Patient context across sessions | Aurora only | **Memory** – short-term + long-term (Patient_Agent continuity, Req 2) |
| Safe agent boundaries | Prompts | **Policy** (preview) – explicit action control |
| Staff / Patient auth | Cognito (custom) | **Identity** – Cognito/IdP integration (Req 1 RBAC) |

---

## Using AgentCore to let the agent access Aurora

**Question:** If Bedrock (Converse) can’t access the Aurora database directly, can I use **Bedrock AgentCore** to access it?

**Answer: Yes.** Bedrock models do not open database connections themselves. Access to Aurora is always through **your** code. AgentCore lets the agent use that code by exposing it as **tools** the model can call.

| Layer | Who accesses Aurora | How |
|-------|----------------------|-----|
| **Converse (current)** | Your Lambda (CDSS router) | Lambda has `get_session()` / Aurora; you fetch data, then pass it to Bedrock for summarization. |
| **AgentCore** | Your **Gateway tools** (Lambda or MCP) | You expose tools like `get_patient`, `list_patients`, `get_surgeries`. The **agent** (Runtime) decides when to call them; the Gateway invokes your Lambda (or MCP server); that Lambda queries Aurora and returns the result to the agent; the agent then generates the reply. |

**Flow with AgentCore:**

1. User asks: *“Give me a summary of patient Harish Menon.”*
2. **AgentCore Runtime** (your agent) has a tool list that includes e.g. `get_patient` or `list_patients`.
3. The agent calls the tool (e.g. `get_patient(name="Harish Menon")` or `get_patient(patient_id="PT-1015")`).
4. **AgentCore Gateway** invokes your **Lambda** (or MCP server) that implements that tool.
5. The Lambda uses **Aurora** (via `DATABASE_URL` / `RDS_CONFIG_SECRET_NAME`, and VPC if needed) to run the query and return the patient record.
6. The agent receives the tool result and generates a natural-language summary for the user.

So the agent “accesses” Aurora only **through tools** you implement and register on the Gateway. The repo already has a **Gateway Lambda** (`gateway_tools_src/lambda_handler.py`) that can talk to Aurora for `get_hospitals` and `get_ot_status` when `RDS_CONFIG_SECRET_NAME` or `DATABASE_URL` is set. To give the agent access to **patients**, **surgeries**, etc., add more tool handlers in that Lambda (e.g. `get_patient`, `list_patients`) that query the CDSS Aurora schema, then register those tools in the AgentCore Gateway and in your agent’s tool list. The Lambda must run in a VPC that can reach Aurora (or use IAM auth and a reachable RDS endpoint), same as the CDSS router Lambda.

---

## AgentCore Capabilities to Adopt

| Capability | Priority | Use Case |
|------------|----------|----------|
| **Runtime** | P0 | Host CDSS agents (e.g. severity assessment and routing) |
| **Gateway** | P0 | Expose Hospital Data MCP, CDSS severity-assessment tools |
| **Observability** | P0 | Trace review, medical audit, debugging |
| **Memory** | P1 | Patient context, repeat visits, follow-up |
| **Identity** | P1 | RMP auth when frontend ready |
| **Policy** | P2 | Stricter safety boundaries (when GA) |
| **Code Interpreter** | P3 | Optional: scoring, travel time calculations |
| **Browser** | P3 | Optional: hospital availability lookup |
| **Evaluations** | P3 | Quality measurement (when GA) |

---

## Architecture (Target)

CDSS aligns with requirements: API Gateway exposes Staff/Patient-facing routes; AgentCore hosts or backs CDSS agents (Patient, Surgery, Resource, Scheduling, Engagement) with Gateway-exposed MCP tools. Traces link to Patient_ID, Doctor_ID for audit (CDSS.mdc).

```
                    ┌─────────────────────────────────────────┐
                    │     API Gateway (CDSS)                   │
                    │  /api/v1/*  /hospitals  /health           │
                    │  POST /api/v1/agent (Supervisor → 5 agents) │
                    └─────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
             ┌──────────┐      ┌──────────────┐   ┌──────────┐
             │ Patient  │      │Hospital Match│   │ Routing  │
             │ Agent    │      │   Lambda     │   │  Lambda  │
             └────┬─────┘      └──────┬───────┘   └────┬─────┘
                  │                   │                 │
                  └───────────────────┼─────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │      Bedrock AgentCore             │
                    │  ┌─────────┐  ┌──────────────┐   │
                    │  │Runtime  │  │   Gateway    │   │
                    │  │(agents) │  │(MCP tools)   │   │
                    │  └────┬────┘  └──────┬───────┘   │
                    │       │              │           │
                    │  ┌────┴──────────────┴───────┐   │
                    │  │ Memory │ Observability    │   │
                    │  └──────────────────────────┘   │
                    └─────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │  Aurora (CDSS: patients, audits,  │
                    │  severity_assessments, hospital_*)   │
                    └──────────────────────────────────┘
```

---

## Phases

### Phase AC-1: Foundation (AgentCore Runtime + Gateway + Observability)

**Goal:** Stand up AgentCore Runtime and Gateway; connect a simple CDSS PoC agent (e.g. hospital/OT status or CDSS severity-assessment stub) and add basic tracing/metrics.

**Deliverables:**
- [ ] AgentCore Runtime workspace/deployment — **Create agent in AWS** via toolkit (`agentcore create` → `agentcore launch`) or Console; see [agentcore-create-agents-in-aws.md](./agentcore-create-agents-in-aws.md). Repo includes minimal `agentcore/agent/main.py` + `requirements.txt`.
- [x] AgentCore Gateway created (script + Console for Lambda target) — **Lambda target added manually** per [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md); API supports only MCP targets.
- [x] A CDSS PoC agent deployed to Runtime (or Lambda calling AgentCore API).
- [x] Terraform: `use_agentcore`, `agent_runtime_arn`, IAM for `InvokeAgentRuntime`.

**After gateway is created:** Add Lambda as target in Console (Bedrock → AgentCore → Gateways → [gateway] → Targets). Then proceed to AC-2 (Triage + Observability) per below.

---

### Phase AC-2: All 5 Agents + Observability

**Goal:** Migrate all 5 CDSS agents to AgentCore; enable full trace observability.

**Deliverables:**
- [ ] All 5 agents (Patient, Surgery, Resource, Scheduling, Engagement) on AgentCore Runtime
- [ ] AgentCore Observability: tracing, CloudWatch dashboards (links to Patient_ID, Doctor_ID per CDSS.mdc)
- [ ] Trace review workflow for Admin/Dev (medical audit; Req 10 audit trails)
- [ ] Gateway tools for all agents: get_patient, list_patients, get_surgeries, get_surgery, get_schedule, find_replacement, get_medications, get_reminders_adherence
- [ ] Persist clinical assessments to Aurora (when tables ready)

---

### Phase AC-3: Memory + Hospital MCP

**Goal:** Add Memory for patient context; integrate Hospital Data MCP via Gateway (Req 8 MCP; CDSS MCP adapter pattern).

**Deliverables:**
- [ ] AgentCore Memory: short-term (session) + long-term (patient) — supports Patient_Agent continuity (Req 2)
- [ ] Gateway: Hospital Data MCP as tool source (and optionally ABDM, OT/resources for CDSS)
- [ ] CDSS agents use real hospital and OT data via MCP/DB (replace stubs)
- [ ] Patient context available across severity assessment → hospital → routing flow

**Phase AC-3: Next steps (after AC-2 is done)**

1. **Enable AgentCore Memory**
   - In AWS Console: Bedrock → AgentCore → your agent/runtime → Memory (or equivalent).
   - Configure short-term (session) memory so the agent retains context within a conversation.
   - Configure long-term (patient) memory so Patient_Agent can persist patient context across sessions (Req 2 continuity).
   - Wire memory ID or session ID from your API (e.g. `memory_id` / `session_id` in `invoke_agent_runtime` payload) so traces and memory align with Patient_ID.

2. **Expose Hospital Data via MCP on the Gateway**
   - Add or register a **Hospital Data MCP** tool source on the existing AgentCore Gateway (Bedrock → AgentCore → Gateways → [gateway] → Targets).
   - If using a Lambda: ensure `get_hospitals`, `get_ot_status` (and any hospital/OT tools) are registered and return real or stub data per [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md).
   - Optionally add ABDM and OT/resources as MCP or Lambda tools on the same Gateway.

3. **Replace stubs with real data**
   - Point Gateway Lambda (or MCP) at live DB: set `RDS_CONFIG_SECRET_NAME` (or `DATABASE_URL`) so `get_hospitals`, `get_ot_status`, and CDSS tools in `lambda_handler.py` query Aurora.
   - Remove or replace synthetic/stub responses in Gateway tools with real hospital and OT data from Aurora (or external MCP).

4. **Patient context across the flow**
   - Ensure severity assessment → hospital match → routing flow share the same patient/session context (e.g. via memory or request payload: `patient_id`, `session_id`, `memory_id`).
   - Verify in traces (CloudWatch / observability) that Patient_ID and Doctor_ID are present for medical audit (CDSS.mdc).

5. **Docs and verification**
   - Update [PROJECT_REFERENCE.md](./PROJECT_REFERENCE.md) with memory config, Gateway tool list, and any new env vars.
   - Add a short verification: one full flow (e.g. "patient summary for PT-1001" → hospital match) that uses memory and real Gateway tools; confirm trace shows patient context and tool calls.
   - **Gateway → Aurora:** When switching from stub to live DB, see [AC3_AURORA_GATEWAY_DEBUG.md](./AC3_AURORA_GATEWAY_DEBUG.md) for connection troubleshooting.

---

### Phase AC-4: Routing + Identity

**Goal:** Add Routing agent; enable Identity for Staff/Patient auth (Req 1 RBAC).

**Deliverables:**
- [ ] Routing agent on AgentCore Runtime
- [ ] POST /route endpoint
- [ ] AgentCore Identity: Cognito/IdP integration for Doctor_Module and Patient_Module (Req 1)
- [ ] Policy (if GA): stricter agent action boundaries

---

## Migration Strategy

1. **Incremental:** Keep Converse API fallback until AgentCore path is stable; then hard cutover (no long-term feature flag).
2. **Feature flags:** `USE_AGENTCORE` env var to toggle during migration; remove once cutover complete.
3. **Preserve contracts:** API request/response schemas unchanged.
4. **Aurora unchanged:** Persistence layer stays; AgentCore replaces only the AI invocation path.

---

## Execution Order

| Phase | Focus | Status | Dependency |
|-------|-------|--------|------------|
| AC-1 | Runtime + Gateway + CDSS PoC agent | Next | None |
| AC-2 | All 5 Agents + Observability | Pending | AC-1 |
| AC-3 | Memory + Hospital MCP | Pending | AC-1, AC-2 |
| AC-4 | Routing + Identity | Pending | AC-1 |

---

## Technical Notes

- **AgentCore SDK:** Python SDK on [GitHub](https://github.com/aws/amazon-bedrock-agentcore-sdk-python)
- **Gateway:** Transforms APIs/Lambda/MCP into tools; MCP support via [Gateway tutorials](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tutorials.html). For CDSS, Gateway can expose Hospital Data, ABDM, OT/resources tools (see [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md)).
- **Runtime:** Serverless; supports extended sessions; any framework (LangGraph, CrewAI, etc.)
- **Region:** AgentCore availability per AWS docs; CDSS data residency and PII in ap-south-1 per [requirements.md](./requirements.md) (Req 10).
- **CDSS.mdc:** All assessment-producing agents must use strict schemas (priority, confidence, risk_factors, surgery readiness), trace review, and safety disclaimers; apply when migrating Patient/Surgery/Engagement agents to AgentCore.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AgentCore API changes / preview features | Pin SDK version; use feature flags |
| Migration breaks existing flows | Keep Converse fallback; A/B test |
| MCP not yet ready | Use Gateway with Lambda/API stubs until MCP available |

---

## Phase AC-1: Immediate Next Steps

1. **Explore AgentCore Console & API**
   - [AgentCore Get Started](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html)
   - [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/develop-agents.html)
   - [AgentCore Python SDK](https://github.com/aws/amazon-bedrock-agentcore-sdk-python)

2. **Create Runtime + Gateway (Terraform or Console)**
   - Provision AgentCore Runtime workspace
   - Configure Gateway with `submit_hospital_matches` (Lambda or synthetic data as tool source)

3. **Wire CDSS Lambda(s) to AgentCore**
   - Add `USE_AGENTCORE` env var; when true, call AgentCore API instead of Converse
   - Preserve request/response contract
   - Converse fallback when `USE_AGENTCORE=false`; hard cutover once stable

4. **Basic tracing/metrics** ✓
   - CloudWatch Logs: `HospitalMatcher source=agentcore|converse|bedrock_agent duration_ms=...`
   - When migrating CDSS agents: include Patient_ID, Doctor_ID, surgery IDs in trace metadata for audit (CDSS.mdc).
