# Backend TODO – AgentCore / Gateway

**Branch:** Create new branch from `main` for next work (e.g. `feature/guardrails`).  
**Last updated:** Feb 2026

---

## Status

- **AC-1 (Gateway + Eka):** Done. Hospital Matcher → Gateway (A), Eka as Gateway target (B), Triage → Eka (C). See [RELEASE-Gateway-Eka-Integration.md](./RELEASE-Gateway-Eka-Integration.md) and [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md).
- **Eka on triage runtime:** Done. Script `scripts/enable_eka_on_runtime.py` sets Gateway env vars on the AgentCore triage runtime. Triage recommendations include Indian medications and treatment protocols. Eka validation (E1–E5) and test cases documented; tested and docs updated. See [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) §4b, [EKA-VALIDATION-RUNBOOK.md](./EKA-VALIDATION-RUNBOOK.md).
- **Google Maps / POST /route:** Done and tested. Real directions when API key is in Secrets Manager; `distance_km`, `duration_minutes`, `directions_url`. See [GOOGLE-MAPS-ACCOUNT-SETUP.md](../infrastructure/GOOGLE-MAPS-ACCOUNT-SETUP.md).
- **AC-2 (Triage on AgentCore):** Done. Triage agent in `agentcore/agent/triage_agent.py`; POST /triage invokes AgentCore; observability in [OBSERVABILITY.md](./OBSERVABILITY.md).
- **AC-3 (Memory + Hospital MCP):** Implemented and tested. Optional `session_id` / `patient_id` on /triage and /hospitals; passed to AgentCore as `runtimeSessionId`. Hospital Matcher uses Gateway get_hospitals. Optional: re-test session continuity (same session_id across triage → hospitals → route).
- **AC-4 (Routing + Identity):** Routing pipeline and RMP auth done. **Guardrails G1–G3 done:** input validation (triage: symptoms/vitals/age; hospitals: severity enum, limit, lat/lon; route: body, lat/lon, address length), output validation (triage/hospitals/route max lengths and enums), safety prompts (AGENT-PROMPTS.md, prompts updated in instructions and agents). **Policy done:** run `scripts/setup_agentcore_policy.py` after gateway setup. See [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) §4, [AGENT-PROMPTS.md](./AGENT-PROMPTS.md), [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md).
- **Hackathon submission:** Docs updated. [HACKATHON.md](../../HACKATHON.md), [API-Integration-Guide.md](../frontend/API-Integration-Guide.md), [triage-api-contract.md](../frontend/triage-api-contract.md).

---

## What to work on next

**Policy (AgentCore Policy is GA):** Implemented. A policy engine is attached to the Gateway via `scripts/setup_agentcore_policy.py`; only whitelisted tools are allowed. See [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md). For per-runtime restriction (Triage vs Hospital Matcher vs Routing), use separate OAuth clients per runtime and extend the Cedar policies as described in the runbook.

**Completed: Guardrails G1–G3** — G1 input validation (triage/hospitals/route), G2 output validation (max lengths, enums, route sanitize), G3 safety prompts ([AGENT-PROMPTS.md](./AGENT-PROMPTS.md), prompts updated in instructions and agents).

**Next (in order):** 1) ~~Redeploy AgentCore~~ ✅ Done; 2) Policy ✅ Implemented ([POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md), `scripts/setup_agentcore_policy.py`); 3) HIPAA H1–H4 ✅ Complete ([HIPAA-Compliance-Checklist.md](./HIPAA-Compliance-Checklist.md)); 4) Comprehensive endpoint testing ([API-TEST-RESULTS.md](./API-TEST-RESULTS.md)); 5) Deploy web app + frontend–backend integration. Full roadmap: [ROADMAP-NEXT.md](../ROADMAP-NEXT.md).

| # | Item | What to do |
|---|------|------------|
| **G1** | **Input validation** | Triage: symptom list length, vitals ranges (e.g. heart_rate 20–300), age 0–150. Hospitals: severity enum, limit bounds. Route: origin/destination lat/lon bounds, no empty payloads. Return **400** with clear message. See [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) §4. |
| **G2** | **Output validation** | Triage: severity enum, confidence 0–1, max recommendations count/length. Hospitals: max hospitals count, max safety_disclaimer length. Route: validate directions response shape. Reject malformed model output; log and return safe fallback or 500. |
| **G3** | **Safety boundaries in prompts** | Document and tighten system prompts for all three agents: “emergency triage / hospital matching / routing only”, “do not prescribe”, “do not replace physician”. Refusal instructions for off-topic queries. See [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) §4, [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) §2. |
| **Policy** | **Agent action boundaries** | Implemented: policy engine on Gateway via [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md) and `scripts/setup_agentcore_policy.py`. |

**References:** [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) §4 (G1–G3 implementation notes), [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) §2.

---

## Order of Work

### Phase 1: Gateway Integration (A → B → C) — Done

1. **A.** Wire Hospital Matcher agent to Gateway — **Done**
2. **B.** Add Eka as Gateway target — **Done**
3. **C.** Wire Triage agent to Eka tools — **Done**

### Phase 2: AgentCore Phases (AC-2 → AC-3 → AC-4)

4. **AC-2.** Triage on AgentCore + Observability — **Done**
5. **AC-3.** Memory + Hospital MCP — **Done** (session_id/patient_id; tested; optional re-test)
6. **AC-4.** Routing + Identity — **Routing pipeline + Google Maps + RMP auth + Guardrails G1–G3 + Policy done.** Policy: run `python3 scripts/setup_agentcore_policy.py` after gateway setup.

---

## Key References

- [NEXT-SESSION.md](./NEXT-SESSION.md) – What to work on next session (create new branch from main)
- [RELEASE-Gateway-Eka-Integration.md](./RELEASE-Gateway-Eka-Integration.md) – AC-1 release notes, config, quick test
- [TESTING-Pipeline-curl.md](./TESTING-Pipeline-curl.md) – Triage → Hospitals → Route curl; use `python3 scripts/get_rmp_token.py`
- [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) – Unit, integration, API tests
- [secrets.md](./secrets.md) – Terraform-created secrets, api_config keys, gateway-config (client_info.scope), load scripts
- [agentcore-implementation-plan.md](./agentcore-implementation-plan.md) – Phases, architecture
- [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md) – Gateway setup, **Eka on triage runtime** (`enable_eka_on_runtime.py`)
- [AGENT-PROMPTS.md](./AGENT-PROMPTS.md) – G3: Agent prompts and safety boundaries (triage, hospital matcher, routing)
- [OBSERVABILITY.md](./OBSERVABILITY.md) – Triage/Hospital Matcher logs, trace review
- [implementation-history.md](./implementation-history.md) – History, fixes
