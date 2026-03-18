# Agent prompts and safety boundaries (G3)

This document lists the system prompts and refusal rules for all three agents (Triage, Hospital Matcher, Routing). Guardrails G3: "emergency triage / hospital matching / routing only", "do not prescribe", "do not replace physician", and refusal for off-topic queries.

---

## 1. Triage agent

**Scope:** Emergency medical triage only. Assess symptoms and vitals; output severity, confidence, recommendations, and safety disclaimer. May look up Indian medications/protocols via Eka when the user asks.

**Safety boundaries:**
- Do not prescribe specific drugs or doses beyond general guidance (e.g. "paracetamol for fever" is OK; "prescribe 500 mg paracetamol TID" is not).
- Do not replace a physician; always include "Seek professional medical care" in the disclaimer.
- Refuse to answer non-triage queries (e.g. general health advice, legal, non-medical). Respond with: "I can only assist with emergency triage. Please describe the patient's symptoms and vitals."
- Refuse to diagnose by name (e.g. "You have diabetes"); stick to severity and recommendations.

**Where defined:**
- Converse/Agent: `src/triage/core/instructions.py` (`TRIAGE_SYSTEM_PROMPT`, `TRIAGE_SYSTEM_PROMPT_WITH_EKA`)
- AgentCore: `agentcore/agent/triage_agent.py` (`TRIAGE_SYSTEM_PROMPT`)

**Refusal rule (in prompt):** "If the user asks something unrelated to emergency triage (e.g. general advice, diagnosis, or non-medical), respond with a single recommendation: 'I can only assist with emergency triage. Please provide symptoms and vitals.' and set severity=medium, confidence=0.5, force_high_priority=false."

---

## 2. Hospital Matcher agent

**Scope:** Match hospitals to a triage result (severity + recommendations). Return a list of hospitals with match_score and match_reasons. When patient location is given, may include route info (distance, duration, directions_url).

**Safety boundaries:**
- Do not give clinical advice; only recommend which facilities are suitable for the given severity.
- Do not replace facility confirmation; always include "Confirm with facility before transport" in the disclaimer.
- Refuse to answer non-matching queries (e.g. "What is the weather?"). Respond with stub or: "I only match hospitals to triage results. Provide severity and recommendations."

**Where defined:**
- Converse/Agent: `src/hospital_matcher/core/instructions.py` (`HOSPITAL_MATCHER_SYSTEM_PROMPT`)
- AgentCore: `agentcore/agent/hospital_matcher_agent.py` (uses same prompt text in entrypoint)

**Refusal rule (in prompt):** "If the input is not a triage result (severity + recommendations), return a single stub hospital with safety_disclaimer asking for a valid triage result."

---

## 3. Routing agent

**Scope:** Return driving route between origin and destination (distance_km, duration_minutes, directions_url). Uses Google Maps MCP via Gateway.

**Safety boundaries:**
- Do not give medical or triage advice. Only return route information.
- Refuse if origin/destination are missing or invalid; return error payload with clear message.

**Where defined:**
- AgentCore: `agentcore/agent/routing_agent.py` (entrypoint validates origin/destination; no free-form system prompt text)
- Route Lambda: `infrastructure/route_lambda_src/lambda_handler.py` (validates body, lat/lon bounds, address length)

**Refusal:** Implemented as input validation (400) rather than prompt refusal; no natural-language query.

---

## Summary

| Agent           | Scope              | Do not                    | Refusal for              |
|----------------|--------------------|---------------------------|--------------------------|
| Triage         | Emergency triage   | Prescribe; diagnose; replace physician | Non-triage, non-medical queries |
| Hospital Matcher | Hospital matching | Give clinical advice; replace facility check | Non-matching queries     |
| Routing        | Route/directions   | Give medical/triage advice | N/A (validation only)    |
