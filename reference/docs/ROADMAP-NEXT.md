# Roadmap: Next phases

Order of work: **1 → 2 → 3 → 4**, then **5 (web app deploy + frontend integration)**.

---

## Phase 1: Redeploy AgentCore (G3 prompts live) ✅ Done

**Goal:** Get the updated G3 safety prompts (refusal, “do not prescribe”) running on all three AgentCore runtimes.

**Status:** Completed. All three runtimes redeployed (Hospital Matcher, Triage + enable_eka_on_runtime, Routing). Tfvars verified; no ARN changes needed for Hospital Matcher or Routing.

**Steps:** See [agentcore/README.md](../agentcore/README.md) § **Redeploy AgentCore**.

- Deploy Hospital Matcher runtime (`hospital_matcher_agent.py`).
- Deploy Triage runtime (`triage_agent.py`), then run `python3 scripts/enable_eka_on_runtime.py` so Eka stays enabled.
- Deploy Routing runtime (`routing_agent.py`).
- Update tfvars if any ARN changed; `terraform apply` if needed.
- Quick verify: triage + hospitals curl; Eka test (Indian paracetamol brands).

---

## Phase 2: Policy (AgentCore Policy is GA) ✅ Done

**Goal:** Restrict which tools can be called through the Gateway; principle of least privilege.

**Status:** Implemented. A policy engine is created and attached to the Gateway.

**Steps (already done):**
- Run `python3 scripts/setup_agentcore_policy.py` after Gateway setup. This creates the policy engine, adds a Cedar permit policy that allows only the whitelisted tools (get_hospitals, Eka tools, get_route, get_directions, geocode_address), and attaches the engine to the Gateway in ENFORCE mode.
- **Runbook:** [POLICY-RUNBOOK.md](backend/POLICY-RUNBOOK.md) — allowlist, how to update, and optional per-runtime restriction with separate OAuth clients.
- See [AC4-Routing-Identity-Design.md](backend/AC4-Routing-Identity-Design.md) §4.

---

## Phase 3: HIPAA / compliance (H1–H4)

**Goal:** Document and harden for health data (PHI scope, encryption, access, audit).

**Steps:** See [ROADMAP-after-AC4.md](backend/ROADMAP-after-AC4.md) §1 and **[HIPAA-Compliance-Checklist.md](backend/HIPAA-Compliance-Checklist.md)** (H1–H4).

| # | Item | Action |
|---|------|--------|
| H1 | Document PHI scope | List what we store (symptoms, vitals, triage result, session/patient ids); classify as PHI/sensitive. |
| H2 | Encryption checklist | Confirm Aurora encryption at rest, TLS in transit, Secrets Manager; document. |
| H3 | Access control | IAM least privilege; no PHI in logs; restrict who can read api_config / gateway-config / eka. |
| H4 | Audit logging | Document request_id, triage_assessments.id, CloudWatch; add who-accessed-what if required. |

---

## Phase 4: AC-3 re-test (session continuity)

**Goal:** Confirm one AgentCore session is reused across triage → hospitals → route when frontend sends the same `session_id`.

**Steps:**

1. Get token: `RMP_TOKEN=$(python3 scripts/get_rmp_token.py)` and `eval $(python3 scripts/load_api_config.py --exports)`.
2. Generate one session_id (e.g. `SESSION_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')`).
3. POST /triage with `"session_id": "<SESSION_ID>"`.
4. POST /hospitals with same `"session_id": "<SESSION_ID>"` and severity/recommendations from triage.
5. Optionally POST /route; same session_id if your API supports it.
6. Confirm responses are correct and (if you have trace) that the same runtime session was used.

See [TESTING-Pipeline-curl.md](backend/TESTING-Pipeline-curl.md).

---

## Phase 5: Deploy web app + frontend–backend integration

**Goal:** Deploy the web dashboard (MedTriage) and wire it to the backend APIs (triage → hospitals → route, auth).

**Backend (already in place):**

- API base URL from Secrets Manager (`eval $(python3 scripts/load_api_config.py --exports)` → `API_URL`).
- RMP auth: Cognito Id Token; see [RMP-AUTH.md](frontend/RMP-AUTH.md).
- Endpoints: GET /health, POST /triage, POST /hospitals, POST /route. See [API-Integration-Guide.md](frontend/API-Integration-Guide.md).

**Frontend (web app):**

- **Location:** `frontend/web/` (Next.js / Vite, TypeScript). See [frontend/web/README.md](../frontend/web/README.md).
- **Integration checklist:**
  1. **Config:** Set API base URL (from env or build-time config). Use same value as `API_URL` from load_api_config (or Terraform output).
  2. **Auth:** Implement Cognito sign-in; get Id Token and send `Authorization: Bearer <IdToken>` on every POST to triage, hospitals, route. See [RMP-AUTH.md](frontend/RMP-AUTH.md).
  3. **Flow:** Implement triage form → POST /triage → show severity + recommendations; then hospital step → POST /hospitals with severity + recommendations + optional patient location; then route step → POST /route with origin/destination → show distance_km, duration_minutes, directions_url (open in Google Maps).
  4. **Session:** Generate one `session_id` (UUID) at flow start; send it in triage and hospitals (and route if supported) for AC-3 memory continuity. See [triage-api-contract.md](frontend/triage-api-contract.md).
  5. **Error handling:** 401 → refresh token or re-login; 400 → show validation message; 500 → generic error.
- **Deploy:** Build and host the web app (e.g. Vercel, S3+CloudFront, or your chosen host). Ensure CORS allows your API Gateway origin if needed; use the same API base URL in production.

**References:**

- [API-Integration-Guide.md](frontend/API-Integration-Guide.md) – Base URL, auth, endpoints, flow.
- [triage-api-contract.md](frontend/triage-api-contract.md) – Triage request/response, session_id, Eka behavior.
- [RMP-AUTH.md](frontend/RMP-AUTH.md) – Cognito sign-in and Id Token.

---

## Summary

| Phase | What | Done when |
|-------|------|-----------|
| 1 | Redeploy AgentCore (all 3 runtimes + enable_eka_on_runtime) | ✅ G3 prompts live; Eka still on triage. |
| 2 | Policy (GA) | ✅ Policy engine on Gateway via `scripts/setup_agentcore_policy.py`; see [POLICY-RUNBOOK.md](backend/POLICY-RUNBOOK.md). |
| 3 | HIPAA H1–H4 | PHI scope, encryption, access, audit documented. See [HIPAA-Compliance-Checklist.md](backend/HIPAA-Compliance-Checklist.md). |
| 4 | AC-3 re-test | session_id continuity verified with curl or frontend. |
| 5 | Web app deploy + frontend integration | App deployed; uses API_URL, Cognito, triage → hospitals → route; session_id sent. |
