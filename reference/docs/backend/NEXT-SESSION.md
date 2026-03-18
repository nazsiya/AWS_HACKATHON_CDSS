# What to work on next (next session)

**Current sequence:** See **[ROADMAP-NEXT.md](../ROADMAP-NEXT.md)** for the full order:  
**1** ~~Redeploy AgentCore~~ ✅ Done → **2** Policy ✅ Done (run `scripts/setup_agentcore_policy.py`) → **3** HIPAA H1–H4 → **4** AC-3 re-test → **5** Deploy web app + frontend–backend integration.

---

## Phase 1: Redeploy AgentCore ✅ Done

Redeployed all three runtimes (Hospital Matcher, Triage + enable_eka_on_runtime, Routing). G3 safety prompts are live; Eka remains enabled on triage.

---

## Phases 2–4: Policy, HIPAA, AC-3

- **2. Policy:** ✅ Done. Policy engine on Gateway via [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md) and `scripts/setup_agentcore_policy.py`.
- **3. HIPAA (H1–H4):** Document PHI scope, encryption, access, audit. [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) §1.
- **4. AC-3 re-test:** Same `session_id` on triage and hospitals; [TESTING-Pipeline-curl.md](./TESTING-Pipeline-curl.md).

---

## Phase 5: Deploy web app + frontend integration

Deploy `frontend/web/` and wire it to the backend: API URL, Cognito auth, triage → hospitals → route flow, session_id. Full checklist: [ROADMAP-NEXT.md](../ROADMAP-NEXT.md) § Phase 5.

---

## Key references

| Doc | Purpose |
|-----|--------|
| [ROADMAP-NEXT.md](../ROADMAP-NEXT.md) | Phases 1–5: Redeploy AgentCore → Policy → HIPAA → AC-3 → Web app + integration |
| [TODO.md](./TODO.md) | Backend TODO and status |
| [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) | §4: G1–G3 implementation notes |
| [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) | §2: Guardrails; §1: HIPAA |
| [TESTING-Pipeline-curl.md](./TESTING-Pipeline-curl.md) | Curl tests; use same session_id for AC-3 re-test |
| [EKA-VALIDATION-RUNBOOK.md](./EKA-VALIDATION-RUNBOOK.md) | Eka E1–E5 (done; reference) |
| [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md) | Gateway setup; use `python3` for scripts |
| [GOOGLE-MAPS-ACCOUNT-SETUP.md](../infrastructure/GOOGLE-MAPS-ACCOUNT-SETUP.md) | Google Maps API key (done; reference) |

---

## Notes from this session

- **Test 4 (POST /hospitals with location) fixed:** RCA done; enrichment no longer calls get_hospitals a second time (uses only lat/lon from agent response). Deployed and re-tested → 200. See [API-TEST-RESULTS.md](./API-TEST-RESULTS.md) § Test 4 RCA. Next: new module when you return.
- **Gateway OAuth:** If setup script is run again and “Gateway already exists, reusing”, the script now updates the Gateway authorizer to the current OAuth so tokens from the secret work (avoids 401 Invalid Bearer token).
- **Route Lambda:** Uses scope from gateway-config secret (`client_info.scope`, e.g. `emergency-triage-hospitals/invoke`), MCP version `2025-03-26`, and http.client to call the Gateway so response body is always captured on 4xx.
- **Python:** Use `python3` in docs and CLI; `python` may not be on PATH (e.g. macOS).
