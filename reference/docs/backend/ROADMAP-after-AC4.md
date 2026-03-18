# Roadmap: After AC-4

**Purpose:** Plan and prioritize work after AC-4 (Routing + Identity). Three themes: **HIPAA / health data compliance**, **accuracy and guardrails**, and **Eka MCP validation**.

---

## 1. HIPAA / health data compliance

**Goal:** Be compliant with healthcare data regulations so the system is suitable for handling protected health information (PHI).

**Context:**
- **HIPAA** (US): Applies if you’re a US covered entity or business associate processing PHI. Key areas: PHI protection, access control, audit logging, encryption (at rest + in transit), minimum necessary use, breach notification.
- **India:** Digital Personal Data Protection Act and sector-specific health data guidance may apply for India-only deployments.
- **This stack:** We already have Aurora (encryption, IAM auth), API Gateway (HTTPS), Secrets Manager, triage/hospital data in DB. We need to explicitly document and harden.

**Proposed TODOs:**

| # | Item | Notes |
|---|------|--------|
| H1 | **Document PHI scope** | List what we store (symptoms, vitals, age, sex, triage result, session/patient ids). Classify as PHI/sensitive. |
| H2 | **Encryption checklist** | Confirm Aurora encryption at rest, TLS in transit (API Gateway, Lambda↔Aurora), Secrets Manager. Document in a compliance checklist. |
| H3 | **Access control** | IAM least privilege; no PHI in CloudWatch log messages (redact or omit); restrict who can read api_config/gateway-config/eka. |
| H4 | **Audit logging** | We have request_id, triage_assessments.id, CloudWatch. Add: who accessed what (e.g. audit table or CloudTrail + log review). |
| H5 | **Data retention & deletion** | Define retention for triage_assessments; soft delete (deleted_at) already present; add purge/anonymize process if required. |
| H6 | **BAA / DPA** | If US HIPAA: AWS BAA in place; document subprocessors. If India: data processing agreement and consent flow. |

**Suggested order:** H1 → H2 → H3 → H4 (then H5, H6 as policy/legal).

---

## 2. Accuracy and guardrails

**Goal:** Strict guardrails so model outputs and user inputs stay in scope, safe, and validated.

**Context:**
- We already have: Pydantic validation (TriageResult, severity enum, confidence 0–1), force_high_priority when confidence < 85%, single-tool/submit_triage_result pattern.
- We can add: input validation (symptom/vital ranges, length limits), output checks (refuse off-topic, blocklisted terms), rate limits, and optional Bedrock Guardrails (content filters, PII redaction).

**Proposed TODOs:**

| # | Item | Notes |
|---|------|--------|
| G1 | **Input validation** | Enforce symptom list length, vitals in reasonable ranges (e.g. heart_rate 20–300), age 0–150, no empty/invalid payloads. Return 400 with clear message. |
| G2 | **Output validation** | Already have severity enum, confidence 0–1. Add: max recommendations count, max length for recommendations/safety_disclaimer; reject if model returns out-of-enum severity. |
| G3 | **Safety boundaries in prompts** | Document and tighten system prompts: “emergency triage only”, “do not prescribe”, “do not replace physician”. Add refusal instructions for non-triage queries. |
| G4 | **Bedrock Guardrails (optional)** | Use Bedrock Guardrails for content filter (e.g. block harmful content), PII redaction in logs if needed. Configure in Terraform or console. |
| G5 | **Rate limiting** | API Gateway throttling or Lambda reserved concurrency to avoid abuse; optional per-user/custom rate limit. |
| G6 | **Trace review for accuracy** | Use existing observability (request_id, severity, confidence) to sample and review triage outcomes; document “treat as high priority” and escalation paths. |

**Suggested order:** G1 → G2 → G3 (quick wins); then G4–G6 as needed. **G1–G3 and Policy are in AC-4 scope** (see [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md)).

---

## 3. Eka MCP – verify we get useful data

**Goal:** Confirm whether the Eka Gateway integration returns real, useful data (Indian drugs, protocols) or only stubs, and document how to get value from it.

**Context:**
- Eka Lambda (`gateway_eka_lambda_src`) calls Eka API when `EKA_CONFIG_SECRET_NAME` is set and secret has `api_key` or `client_id`. Otherwise it returns stub data.
- Triage (Converse and AgentCore triage_agent) can call `search_indian_medications` and `search_treatment_protocols` when Gateway env vars are set. The model may or may not call these tools depending on the case.

**Proposed TODOs:**

| # | Item | Notes |
|---|------|--------|
| E1 | **Eka secret and config check** | Confirm eka_api_key is set in Terraform (or secret exists), Eka Lambda has EKA_CONFIG_SECRET_NAME, and Gateway has Eka target. **Runbook:** [EKA-VALIDATION-RUNBOOK.md](./EKA-VALIDATION-RUNBOOK.md) §E1. |
| E2 | **Direct Eka Lambda test** | Invoke the Eka Lambda with test events (e.g. drug_name "Paracetamol", protocols query) and log response: real list vs stub. **Runbook:** [EKA-VALIDATION-RUNBOOK.md](./EKA-VALIDATION-RUNBOOK.md) §E2. |
| E3 | **Eka response shape doc** | Document actual JSON shape for medications and protocols; when stub is returned. **Runbook:** [EKA-VALIDATION-RUNBOOK.md](./EKA-VALIDATION-RUNBOOK.md) §E3. |
| E4 | **Triage flow that uses Eka** | Run a triage request where the model is likely to call Eka (e.g. drug name in symptoms or “suitable medication”) and confirm in logs/traces that Gateway was called and tool result returned. **Runbook:** §E4. |
| E5 | **Decide “useful” bar** | If Eka returns real data: document sample queries and use in testing. If only stub: document “Eka stub mode” and steps to enable real Eka (key, API contract). |

**Suggested order:** E1 → E2 → E3 → E4 → E5.

---

## Recommended overall order

1. **AC-4** (current): Routing pipeline **done** (POST /route returns stub; add Google Maps key for real directions). Remaining: guardrails G1–G3, Policy. Create new branch from `main` to continue; see [NEXT-SESSION.md](./NEXT-SESSION.md).
2. **Eka validation (E1–E5):** Quick to do, answers “are we getting anything useful?” and unblocks content/accuracy work.
3. **HIPAA / compliance (H1–H4):** Document PHI, encryption, access, audit — then policy (H5–H6).
4. **Optional:** G4 (Bedrock Guardrails), G5 (rate limits), G6 (trace review).

---

## Next TODO list (to drop into TODO.md after AC-4)

**Done:** AC-4 routing pipeline (POST /route, Gateway maps target, RMP auth). See [NEXT-SESSION.md](./NEXT-SESSION.md) for next steps.

**Phase 3: Compliance, Eka**
- **Eka:** E1–E5 (verify Eka MCP returns useful data; document stub vs real).
- **HIPAA / health data:** H1–H4 (PHI scope, encryption, access, audit).

(Guardrails G1–G3 and Policy are **in AC-4 scope**; see [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md).)
