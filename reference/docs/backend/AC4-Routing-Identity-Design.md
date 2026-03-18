# AC-4: Routing + Identity – Design

**Purpose:** Define AC-4 with (1) **multi-agent routing** (Routing agent called by Hospital Matcher), (2) **Google Maps MCP** for directions/ETA, (3) **tracing and log delivery in every agent**, and (4) **hardened policies and guardrails** (brought forward from post-AC-4 roadmap).

**Product decisions (cost, RMP auth, hospital data):** [AC4-Product-Decisions.md](./AC4-Product-Decisions.md).

---

## 1. Multi-agent: Routing as agent called by Hospital Matcher

**Decision:** Routing is implemented as a **separate agent on AgentCore Runtime**, exposed to Hospital Matcher via the **Gateway** as a tool. That makes the system multi-agent: Hospital Matcher can call the Routing agent when it needs directions/ETA.

**Flow:**

- **Option A – Combined response (chosen):**  
  Frontend calls **POST /hospitals** with triage result + optional patient location (lat/lon or address). Hospital Matcher agent runs, calls Gateway tool `get_hospitals`, then (when patient location is provided) calls Gateway tool **`get_route`** / `get_directions`. Response includes hospitals **and** per-hospital route info (distance, ETA, directions link). POST /route remains for “route only” (e.g. user already selected a hospital).

**Implementation:**

| Component | Responsibility |
|-----------|-----------------|
| **Routing agent** | New agent in `agentcore/agent/routing_agent.py`. Inputs: **origin** and **destination** each as **lat/lon or address string** (user-friendly). When address is provided, backend uses **Geocoding** (Google) to get coordinates. Uses **Google Maps** (Directions / Distance Matrix) via Gateway when configured. Returns structured route info (distance_km, duration_minutes, directions_url). |
| **Gateway** | New target: **maps target** (Lambda calling Google Directions + Geocoding). Tool e.g. `get_directions` and optionally `geocode_address`. Routing agent and Hospital Matcher use these tools. |
| **Hospital Matcher agent** | Add **`get_route_tool`** (origin + destination: lat/lon or address) that calls Gateway. When patient location + hospital locations are available, agent calls this tool and includes **per-hospital route info in the same response** (Option A). |
| **POST /route** | Lambda invokes Routing agent. Body: `origin` and `destination` each as `{ "lat", "lon" }` or `{ "address": "..." }` or `hospital_id`. Standard validation: one origin, one destination; coordinate bounds. |

**Why this is multi-agent:** Hospital Matcher and Routing are two agents. Hospital Matcher does not “contain” routing logic; it **invokes** the Routing agent via a Gateway tool. That keeps concerns separated and allows Routing to be reused from POST /route and from any future caller.

---

## 2. Google Maps MCP for Routing

**Goal:** Use real directions/distance/ETA in the Routing agent via a **Google Maps MCP** integration.

**Options:**

- **A. Gateway target = Lambda that calls Google Maps APIs**  
  A Lambda implements the Gateway tool `get_route`. It calls Google Directions API (and optionally Distance Matrix API) with origin/destination, returns distance, duration, and optionally a deep link or directions URL. The Routing agent then calls this tool via Gateway (same pattern as `get_hospitals` and Eka). No separate “Google MCP server” required; the Lambda is the MCP tool implementation.

- **B. Third-party Google Maps MCP server**  
  If a community or vendor MCP server for Google Maps exists, it can be registered as a Gateway target (e.g. via MCP-over-HTTP). Gateway would expose its tools (e.g. `get_directions`) to the Routing agent.

**Recommended for hackathon:** **Option A** – Lambda that wraps Google Directions API, registered as a Gateway target (e.g. `maps-target`). Routing agent gets a tool `get_directions(origin_lat, origin_lon, dest_lat, dest_lon)` or equivalent. Config: store Google Maps API key in Secrets Manager (e.g. `google_maps_api_key` or in existing api_config); Lambda reads it at runtime. Terraform: new Lambda + optional secret; Gateway setup script adds the new target.

**Config placeholder:** In `gateway_config.json` or api_config secret, add:

- `maps_target_name`: e.g. `maps-target`
- `maps_lambda_arn`: ARN of the Lambda that implements the Directions (and optionally Distance Matrix) call.

**Routing agent behavior:** When Gateway is configured and maps target is present, Routing agent calls the maps tool for each origin–destination pair. When not configured, return stub (e.g. “Routing data not available” or synthetic ETA).

---

## 3. Tracing and log delivery in every agent

**Requirement:** Every agent path (Triage, Hospital Matcher, Routing) must emit **consistent tracing and log delivery** for observability and medical/operational audit.

**Standard log fields (all agents):**

| Field | Meaning | Example |
|-------|--------|--------|
| `source` | Invocation path | `agentcore` or `converse` / `bedrock_agent` |
| `duration_ms` | End-to-end latency | Float |
| `request_id` | Correlation ID (Lambda `aws_request_id` or explicit UUID) | For triage: also persist in DB |

**Where:**

- **Triage:** Already logs `Triage source=... duration_ms=...` and `Triage success request_id=...`. Keep and ensure both AgentCore and Converse paths set these.
- **Hospital Matcher:** Already logs `HospitalMatcher source=... duration_ms=...` and `HospitalMatcher success request_id=...`. Ensure AgentCore path is included.
- **Routing:** New. Routing Lambda must log:
  - `Routing source=agentcore duration_ms=...` (or `converse` if we add a fallback).
  - `Routing success request_id=...` (use `aws_request_id` or generated UUID).

**Checklist (every agent):**

- [ ] Triage: `source` and `duration_ms` on every invocation; `request_id` on success.
- [ ] Hospital Matcher: same.
- [ ] Routing: same (add in AC-4).
- [ ] No PHI in log messages (redact or omit; see H3 in ROADMAP-after-AC4.md).
- [ ] CloudWatch Logs Insights queries in OBSERVABILITY.md cover all three agents.

**Optional (later):** AgentCore Runtime spans/traces in the Bedrock console; link to `request_id` where possible.

---

## 4. Hardened policies and guardrails (in AC-4 scope)

We bring forward from [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) the following so that **all agents** are hardened in AC-4:

**From roadmap – Accuracy and guardrails (G1–G3 + Policy):**

| # | Item | Scope in AC-4 |
|---|------|----------------|
| **G1** | **Input validation** | Apply to **Triage**, **Hospital Matcher**, and **Route** requests: symptom list length, vitals ranges (e.g. heart_rate 20–300), age 0–150, coordinate bounds, no empty/invalid payloads. Return 400 with clear message. |
| **G2** | **Output validation** | Triage: severity enum, confidence 0–1, max recommendations count/length. Hospital Matcher: max hospitals count, max safety_disclaimer length. Route: max fields/length for directions. Reject out-of-enum or malformed model output. |
| **G3** | **Safety boundaries in prompts** | Document and tighten **system prompts** for all three agents: “emergency triage / hospital matching / routing only”, “do not prescribe”, “do not replace physician”. Add refusal instructions for off-topic or non-emergency queries. |
| **Policy** | **Stricter agent action boundaries** | **Done.** AgentCore Policy is GA. Policy engine attached to Gateway via `scripts/setup_agentcore_policy.py`; only whitelisted tools allowed. See [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md). |

**Implementation notes:**

- **G1:** Pydantic models and validator helpers in each Lambda (or shared validation module). Route request: validate origin/destination lat/lon ranges and optional hospital_id format.
- **G2:** After agent response, validate structure and enums before returning; on failure log and return safe fallback or 500 with no raw model output in body.
- **G3:** Central place (e.g. `docs/backend/AGENT-PROMPTS.md`) listing each agent’s system prompt and refusal rules; update agent code to use them.
- **Policy:** Policy engine on Gateway; run `python3 scripts/setup_agentcore_policy.py` after gateway setup. See [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md).

---

## 5. Identity (RMP auth)

**Decision:** **Defer** (see [AC4-Product-Decisions.md](./AC4-Product-Decisions.md)). Document that POST /triage, /hospitals, /route can optionally accept an identity token (Cognito/IdP); implement when frontend has login.

**Update (implemented):** RMP auth is now implemented. POST /triage, /hospitals, and POST /route require a valid Cognito Id token (see [RMP-AUTH.md](../frontend/RMP-AUTH.md) for frontend integration).

---

## 6. Summary: AC-4 deliverables

| # | Deliverable | Notes |
|---|-------------|--------|
| 1 | Routing agent on AgentCore Runtime | `agentcore/agent/routing_agent.py`; uses Gateway tool for maps when configured. |
| 2 | Gateway: routing target + optional Google Maps target | `get_route` (and optionally maps) tool; Hospital Matcher can call it. |
| 3 | Hospital Matcher: `get_route_tool` via Gateway | Multi-agent: Hospital Matcher calls Routing via Gateway. |
| 4 | POST /route endpoint | Lambda invokes Routing agent; same tracing pattern as Triage/Hospital Matcher. |
| 5 | Tracing and log delivery in every agent | Triage, Hospital Matcher, Routing all log source=, duration_ms=, request_id=; doc in OBSERVABILITY.md. |
| 6 | Google Maps MCP (Lambda as Gateway target) | Lambda calling Directions API; key in Secrets Manager; optional. |
| 7 | Guardrails G1–G3 + Policy | Input/output validation and safety prompts for all agents; Policy implemented (runbook + setup_agentcore_policy.py). |
| 8 | Identity (Cognito/IdP) for RMP | **Defer** – document design; implement when frontend ready. |
| 9 | Hospital data (Bangalore + Chennai) | Add from internet (Places/OSM); name, address, lat, lon for routing. |

---

## 7. References

- [agentcore-implementation-plan.md](./agentcore-implementation-plan.md) – Phases, architecture
- [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) – G1–G6, H1–H6, E1–E5
- [OBSERVABILITY.md](./OBSERVABILITY.md) – Log fields, CloudWatch queries
- [gateway_config.json](../../gateway_config.json) – Gateway and target config
