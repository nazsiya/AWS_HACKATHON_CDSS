# Implementation Plan: AI Layer + Backend Services

**Scope:** AI layer (Bedrock, severity classification, confidence scoring, multi-model consensus) and backend Lambda services.  
**Out of scope (other team):** Frontend, Auth, MCP servers, External integrations.

> **See also:** [implementation-history.md](./implementation-history.md) – Full discussion summary, decisions, issues & fixes.

---

## Captured Decisions

| Topic | Decision |
|-------|----------|
| **confidence < 85% → high priority** | Enforced by **reasoning agent** via action group (not post-processing only) |
| **Severity/confidence schema** | **Strict schema** required; align with WHO IITT / ESI |
| **Trace review (medical audit)** | **Admin** and **Dev** review traces |
| **Load tests** | Not now; follow standard practices for timeouts |
| **Tools in critical path** | Required only; no overengineering |
| **Severity/confidence values** | Follow WHO/ESI standards; refer to web for current practices |
| **Action groups** | **Lambda + Knowledge Base** |
| **Model** | **Claude Sonnet** |
| **force_high_priority** | Implement as **action group** |
| **Multi-model** | Phase 3; multiple agents |
| **Knowledge Base** | WHO guidelines via MCP or Aurora; RAG for validation. No prod data for hackathon—use MCP or synthetic data |
| **Triage** | Converse API with tool use (faster iteration); Bedrock Agent optional |
| **Hospital Matcher & Routing** | Migrating to **Bedrock AgentCore** (Runtime, Gateway, Observability); Converse API fallback until ready |

---

## Phase 1: Triage Lambda + Bedrock Converse API ✅ DONE

**Goal:** End-to-end triage flow. Receive symptoms/vitals, return severity + confidence + recommended actions.

**Implemented:** Converse API with tool use (Bedrock Agent path exists but optional; `BEDROCK_AGENT_ID` empty).

### Architecture (Current)
- **Triage**: Converse API + `submit_triage_result` tool; Pydantic validates output
- **force_high_priority**: Enforced in agent instructions and validation
- No Bedrock Agent, no KB for Phase 1 (simplified delivery)

### Deliverables
- [x] **Models** (`src/triage/models/`): TriageRequest, TriageResult, SeverityLevel
- [x] **Core** (`src/triage/core/`): agent.py, instructions.py, tools.py
- [x] **API** (`src/triage/api/`): Lambda handler for POST /triage
- [x] **Infra:** Triage Lambda, API Gateway POST /triage, Bedrock IAM
- [ ] **Agent setup** (optional): Bedrock Agent, action groups, KB – deferred

---

## Phase 2: Aurora Schema + Persist Triage Results ✅ DONE

**Goal:** Store triage assessments in Aurora for audit and downstream use.

### Schema decisions (from discussion)
- **deleted_at**: Yes (soft delete)
- **updated_at**: No (append-only)
- **submitted_by / rmp_id**: Yes
- **hospital_match_id**: Yes (Phase 4 linkage)

### Deliverables
- [x] Aurora schema: `triage_assessments` table (see `infrastructure/migrations/001_*`)
- [x] `src/triage/core/db.py`: IAM auth, insert
- [x] Triage Lambda: persist after assessment
- [x] Infra: Lambda in VPC, NAT, Aurora SG, RDS Data API for migrations

---

## Phase 3: Multi-Model Consensus + Safety Guardrails

**Goal:** Use 2+ Bedrock models for critical cases; stricter safety rules; multiple agents.

### Deliverables
- [ ] Multi-model: invoke 2 models for severity=critical, consensus logic
- [ ] Multiple agents: Triage, Hospital Matcher, Routing
- [ ] Request additional info when symptom data incomplete
- [ ] Flag cases for human review (complex multi-system symptoms)
- [ ] Structured triage report with safety disclaimers
- [ ] Trace review: Admin + Dev for medical audit

---

## Phase 4: Hospital Matcher + Routing Services

**Goal:** Hospital Matcher and Routing using **Bedrock Agents** (per discussion). Stubs until MCP integration.

### Deliverables
- [x] **Hospital Matcher Lambda**: Converse API + optional Bedrock Agent; POST /hospitals
- [x] **API Gateway**: /hospitals
- [x] **hospital_matches** schema; link to `triage_assessments.hospital_match_id`
- [ ] **AgentCore migration**: See [agentcore-implementation-plan.md](./agentcore-implementation-plan.md)
- [ ] **Routing Agent**: AgentCore Runtime; POST /route

---

## Knowledge Base Strategy

| Item | Approach |
|------|----------|
| **WHO guidelines** | Fetch via MCP or store in Aurora |
| **Prod data** | None for hackathon |
| **Hackathon data** | MCP or synthetic data |
| **RAG** | Use for validation against medical protocols |

---

## Execution Order

| Phase | Focus                    | Status   | Dependency |
|-------|--------------------------|----------|------------|
| 1     | Triage + Converse API    | ✅ Done  | None       |
| 2     | Aurora persist           | ✅ Done  | Phase 1    |
| 3     | Multi-model + guardrails | Next     | Phase 1    |
| 4     | Hospital + Routing (Bedrock Agents) | Next | Phase 1    |

Phase 2 and 3 can run in parallel after Phase 1.
