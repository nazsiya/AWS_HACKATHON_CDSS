# API test results (all 3 agents + MCPs)

**Purpose:** Single place to see what is working vs not. Use this for **comprehensive endpoint testing** before moving to the next phase (e.g. web app integration). Re-run the curl commands below to refresh the status table.

---

## Comprehensive endpoint testing (run before Phase 5)

Run all of the following in order and record results in the **Status table** below. From project root:

```bash
eval $(python3 scripts/load_api_config.py --exports)
export RMP_TOKEN=$(python3 scripts/get_rmp_token.py)
BASE="${API_URL%/}"
# 1. Health
curl -s -w "\nHTTP:%{http_code}" "${BASE}/health" && echo ""
# 2. Triage
curl -s -w "\nHTTP:%{http_code}" -X POST "${BASE}/triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"symptoms":["chest pain"],"age_years":50,"sex":"M"}' && echo ""
# 3. Hospitals (no location)
curl -s -w "\nHTTP:%{http_code}" -X POST "${BASE}/hospitals" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"severity":"high","recommendations":["Emergency department"],"limit":2}' && echo ""
# 4. Hospitals (with location) – use limit=1 (skip-enrich fix reduces Gateway calls; may still 504 if slow)
curl -s -w "\nHTTP:%{http_code}" --max-time 45 -X POST "${BASE}/hospitals" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"severity":"high","recommendations":["Emergency department"],"limit":1,"patient_location_lat":12.97,"patient_location_lon":77.59}' && echo ""
# 5. Route
curl -s -w "\nHTTP:%{http_code}" -X POST "${BASE}/route" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"origin":{"lat":12.97,"lon":77.59},"destination":{"lat":12.8967,"lon":77.5982}}' && echo ""
# 6. Eka get_protocol_publishers (direct Lambda – new Gateway tool)
aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"get_protocol_publishers"}' eka_out.json; cat eka_out.json | head -3
# 7. Eka search_pharmacology (direct Lambda – new Gateway tool)
aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"search_pharmacology","query":"Paracetamol"}' eka_out.json; cat eka_out.json | head -5
```

Optional: run **Eka MCP tests** (see table in § Eka MCP tests) to confirm Indian medications and protocols. Once all rows in the Status table are ✅, proceed to the next phase (e.g. deploy web app + frontend integration).

---

## One curl per endpoint

From project root, set env then run each:

```bash
eval $(python3 scripts/load_api_config.py --exports)
export RMP_TOKEN=$(python3 scripts/get_rmp_token.py)
BASE="${API_URL%/}"
```

| # | Endpoint | Curl | Notes |
|---|----------|------|--------|
| 1 | **GET /health** | `curl -s -w "\n%{http_code}" "${BASE}/health"` | No auth. |
| 2 | **POST /triage** | `curl -s -w "\n%{http_code}" -X POST "${BASE}/triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"symptoms":["chest pain"],"age_years":50,"sex":"M"}'` | Triage agent + optional Eka MCP. |
| 3 | **POST /hospitals** (no location) | `curl -s -w "\n%{http_code}" -X POST "${BASE}/hospitals" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"severity":"high","recommendations":["Emergency department"],"limit":2}'` | Hospital Matcher agent + get_hospitals MCP. |
| 4 | **POST /hospitals** (with patient location) | `curl -s -w "\n%{http_code}" -X POST "${BASE}/hospitals" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"severity":"high","recommendations":["Emergency department"],"limit":2,"patient_location_lat":12.97,"patient_location_lon":77.59}'` | Uses get_route (Routing agent → maps MCP) for directions_url per hospital; can timeout if enrichment is slow. |
| 5 | **POST /route** | `curl -s -w "\n%{http_code}" -X POST "${BASE}/route" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"origin":{"lat":12.97,"lon":77.59},"destination":{"lat":12.8967,"lon":77.5982}}'` | Route Lambda → Gateway maps-target → gateway_maps Lambda (Google Maps). |
| 6 | **Eka get_protocol_publishers** | `aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"get_protocol_publishers"}' eka_out.json && cat eka_out.json \| jq .` | Direct Lambda; expect JSON with `publishers`. |
| 7 | **Eka search_pharmacology** | `aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"search_pharmacology","query":"Paracetamol"}' eka_out.json && cat eka_out.json \| jq .` | Direct Lambda; expect pharmacology results. |

---

## Status table (working vs not)

| Endpoint | Agent / MCP | Expected | Last run result | Working? |
|----------|-------------|----------|-----------------|----------|
| **GET /health** | — | 200, `{"status":"ok",...}` | 200 | ✅ Yes |
| **POST /triage** | Triage AgentCore, optional Eka MCP | 200, `severity`, `recommendations`, `session_id` | 200, severity critical | ✅ Yes |
| **POST /hospitals** (no location) | Hospital Matcher AgentCore, get_hospitals MCP | 200, `hospitals` (e.g. blr-apollo-1), `safety_disclaimer` | 200, real hospitals | ✅ Yes |
| **POST /hospitals** (with patient location) | Hospital Matcher + get_route → Routing agent → maps MCP | 200, each hospital has `directions_url`, `distance_km`, `duration_minutes` | 200 (fix deployed: no 2nd get_hospitals in enrich) | ✅ Yes |
| **POST /route** | Route Lambda → maps-target (get_directions) | 200, `distance_km`, `duration_minutes`, `directions_url` | 200 | ✅ Yes |
| **Eka get_protocol_publishers** | Direct Lambda invoke (Gateway tool) | 200, JSON with `publishers` | 200, publishers list (ICMR, RSSDI, etc.) | ✅ Yes |
| **Eka search_pharmacology** | Direct Lambda invoke (Gateway tool) | 200, JSON with pharmacology results | 200, Paracetamol dose/indications | ✅ Yes |

## Test 4 RCA (POST /hospitals with location → 504)

**Root cause:** AWS API Gateway REST API has a **hard maximum integration timeout of 29 seconds**. The Hospital Matcher Lambda can be set to 60s, but API Gateway stops waiting at 29s and returns **504 Gateway Timeout** if the Lambda has not responded by then.

**Why the request takes so long:** With `patient_location_lat` / `patient_location_lon`, the flow is:

1. **Lambda** invokes the **AgentCore Hospital Matcher runtime** (one blocking call).
2. **Inside the runtime** the agent:
   - Calls **get_hospitals** via the Gateway (one round trip: runtime → Gateway → get_hospitals Lambda).
   - For **each** hospital, calls **get_route** via the Gateway (runtime → Gateway → routing Lambda → maps). Each get_route can take 10–20+ seconds (routing + Google Maps).
3. **After** the agent returns, the code used to always call **`_enrich_hospitals_with_routes`**, which did **get_hospitals again** and **get_route again** for each hospital to “guarantee” directions. So we were doing **get_hospitals twice** and **get_route twice per hospital** even for `limit=1` → **4 Gateway calls** in one request. That easily exceeds 29s, so **limit=1 still hit 504**. A further cause: when the agent did not add route info, **enrichment** called **get_hospitals again** (to resolve lat/lon) then get_route per hospital → **2× get_hospitals + N× get_route**, still over 29s for limit=1.

**What was fixed:** In `agentcore/agent/hospital_matcher_agent.py`, **enrichment is now skipped** when the agent has already added `directions_url` and `distance_km` for all hospitals. That removes the duplicate get_hospitals + get_route calls when the agent does its job, so we only do 1 get_hospitals + N get_route (N = limit) instead of 2 + 2N. For `limit=1` that’s 2 calls instead of 4, which may fit within 29s depending on latency.

**What remains:** Even with 2 calls (get_hospitals + one get_route), total time can still approach or exceed 29s (e.g. cold start, slow maps, or routing agent). So 504 can still occur. Options if it does:

- **Return 200 without route info:** When patient location is present, return hospitals quickly without `distance_km` / `directions_url` and let the client call **POST /route** for the chosen hospital.
- **Separate “enrich” step:** Return 200 with hospitals first; client or a second request asks for “add directions for these hospitals” (e.g. async or a dedicated endpoint).

**Mitigation in tests:** Use `limit=1` for the “with location” test; if 504 persists, treat it as a known platform limit and document that production may need one of the options above.

---

- **POST /route 502/500:** Run `python3 scripts/setup_agentcore_gateway.py` so **gateway_config** secret has `gateway_url` and `client_info`. Ensure **google_maps_api_key** is set in tfvars and Terraform applied so gateway_maps Lambda has the key. If Policy is ENFORCE and route returns "Tool Execution Denied", the Cedar action/resource at request time may not match the policy; use `python3 scripts/setup_agentcore_policy.py --log-only` so route works, then check Observability for the actual Cedar request.
- **POST /hospitals with location → 504:** **RCA:** API Gateway has a **maximum integration timeout of 29 seconds**. The Hospital Matcher agent (with patient location) calls get_route per hospital to enrich with distance/directions; with limit=2 this can exceed 29s. **Fix:** Enrichment no longer calls get_hospitals again; it uses only lat/lon from the agent's hospital objects. Redeploy: `agentcore deploy --agent hospital_matcher_agent` then `python3 scripts/enable_gateway_on_hospital_matcher_runtime.py`. Use `limit=1` for the test.
- **401 on any POST:** Get a fresh RMP token: `RMP_TOKEN=$(python3 scripts/get_rmp_token.py)`.

---

## Eka MCP tests (POST /triage with Eka-triggering prompts)

Eka is **not** a separate REST API; it is used by the **Triage agent** via the Gateway when the user asks for Indian medications or treatment protocols. The Gateway calls the Eka Lambda tools: `search_medications` (→ `search_indian_medications`), `search_protocols` (→ `search_treatment_protocols`). Full test cases: [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) §4b.

**Prereq:** Triage runtime has Gateway env vars; run `python3 scripts/enable_eka_on_runtime.py` after triage deploy.

| Test | Eka feature | Symptoms (request) | Last run | Pass criteria |
|------|------------|-------------------|----------|----------------|
| **M1** | search_indian_medications | `["fever", "patient wants Indian paracetamol brands"]` | 200 | ✅ Indian brands in recommendations (e.g. Crocin, Calpol, Dolo, Paracip) |
| **M2** | search_indian_medications | `["sore throat", "need Indian amoxicillin or equivalent"]` | 200 | ✅ 200; Indian brands may or may not appear (model-dependent) |
| **M5** | search_indian_medications | `["diabetes", "patient asks for metformin brands available in India"]` | 200 | ✅ Indian metformin brands (e.g. Glycomet, Diabex, Glucophage) |
| **P1** | search_treatment_protocols | `["fever", "what is the recommended treatment protocol for fever?"]` | 200 | ✅ Protocol-style steps (monitor temp, dosing, danger signs) |
| **P2** | search_treatment_protocols | `["high blood sugar", "diabetes management protocol"]` | 200 | ✅ Protocol-style guidance (glucose check, DKA signs, referral) |
| **P4** | search_treatment_protocols | `["acute diarrhoea", "ORS and dehydration protocol"]` | 200 | ✅ ORS/WHO-ORS, dehydration signs, zinc supplementation |
| **C1** | both | `["fever and cough", "Indian paracetamol brands and fever protocol"]` | 200 | ✅ Indian brands (Crocin, Dolo) + protocol steps |

**Other Eka Lambda tools** (now on Gateway and in policy): `get_protocol_publishers`, `search_pharmacology`. Test via **POST /triage** with prompts below, or **direct Lambda invoke** (curl examples in § New Eka tools: get_protocol_publishers, search_pharmacology).

**Quick curl (Eka medications + protocol):**

```bash
eval $(python3 scripts/load_api_config.py --exports)
export RMP_TOKEN=$(python3 scripts/get_rmp_token.py)
curl -s -X POST "${API_URL}triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" \
  -d '{"symptoms": ["fever", "patient wants Indian paracetamol brands"]}' | jq .recommendations
curl -s -X POST "${API_URL}triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" \
  -d '{"symptoms": ["acute diarrhoea", "ORS and dehydration protocol"]}' | jq .recommendations
```

---

## New Eka tools: get_protocol_publishers, search_pharmacology

These two tools are on the Gateway (Eka target) and in the policy allowlist. Test them via **POST /triage** (if the triage agent calls them) or **direct Lambda invoke**.

### Via POST /triage (prompts that may trigger the tools)

| Tool | Test | Pass criteria |
|------|------|---------------|
| **get_protocol_publishers** | `curl -s -w "\n%{http_code}" -X POST "${BASE}/triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"symptoms":["diabetes","which protocol publishers are available for treatment protocols?"],"age_years":45,"sex":"F"}'` | 200; recommendations may reference publishers (ICMR, RSSDI) |
| **search_pharmacology** | `curl -s -w "\n%{http_code}" -X POST "${BASE}/triage" -H "Content-Type: application/json" -H "Authorization: Bearer $RMP_TOKEN" -d '{"symptoms":["fever","what is paracetamol dosing and safety in pregnancy?"],"age_years":30,"sex":"F"}'` | 200; recommendations may include dosing/safety (NFI-style) |

Use same `eval` and `RMP_TOKEN` as in § Comprehensive endpoint testing; `BASE="${API_URL%/}"`.

### Via direct Lambda invoke (AWS CLI)

```bash
eval $(python3 scripts/load_api_config.py --exports)
# get_protocol_publishers (no extra params)
aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"get_protocol_publishers"}' eka_out.json && cat eka_out.json | jq .

# search_pharmacology (query required for meaningful result)
aws lambda invoke --function-name "$GATEWAY_EKA_LAMBDA_ARN" --payload '{"tool":"search_pharmacology","query":"Paracetamol"}' eka_out.json && cat eka_out.json | jq .
```

(Use `--cli-binary-format raw-in-base64-out` with **AWS CLI v2** if your payload is raw JSON; omit for CLI v1.) Run from project root so `eka_out.json` is written in the repo (or use `/tmp/eka_out.json` if you prefer). Expected: JSON body with `publishers` (get_protocol_publishers) or pharmacology results (search_pharmacology). Check the output file for Eka API errors.
