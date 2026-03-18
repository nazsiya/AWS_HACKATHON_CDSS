# AgentCore Policy runbook (Policy is GA)

**Purpose:** Restrict which Gateway tools agents can call (principle of least privilege). Policy in Amazon Bedrock AgentCore is **generally available** and enforced on our Gateway.

**Status:** Implemented. A policy engine is created and attached to the Gateway via `scripts/setup_agentcore_policy.py`. The allowlist must contain **only tools that actually exist on the gateway** (see [POLICY-RCA.md](./POLICY-RCA.md)). Wrong format or listing tools not in the gateway schema causes "unrecognized action."

- **Why the two policies showed "Create failed":** Policies are validated against a Cedar schema that is **generated from the Gateway's MCP tool manifest**. That schema is only available **after** the policy engine is **attached to the gateway**. The script used to create policies before attaching the engine, so validation had no schema and creation failed. **Fix:** The script now attaches the policy engine to the gateway first, waits for schema propagation, then creates policies. Re-run `python3 scripts/setup_agentcore_policy.py` to delete failed policies and create fresh ones (they should show Active).

**ENFORCE vs LOG_ONLY:** With **ENFORCE**, direct HTTP callers (e.g. Route Lambda calling `maps-target___get_directions`) may still get "Tool Execution Denied" if the action or resource in the Cedar request at runtime does not exactly match the policy (e.g. different action identifier format). Use **LOG_ONLY** so all tool calls succeed while you verify the exact request shape in Observability: `python3 scripts/setup_agentcore_policy.py --log-only`. Then switch back to ENFORCE once policies match.

---

## Why Policy matters

Each AgentCore runtime that uses the Gateway (Triage, Hospital Matcher, Routing) could theoretically call any Gateway tool. Policy enforces a **whitelist**: only the tools we explicitly permit are allowed. Any other tool call is denied at the Gateway boundary.

---

## Implemented: tool allowlist

We use **one policy engine** on the single Gateway. **Correct Cedar format:** actions = `target___tool` (triple underscore); resource = `AgentCore::Gateway::"<gateway ARN>"`. **Critical:** Only list tools that **exist on the gateway** (in its schema). Listing a tool that is not registered on the gateway causes "unrecognized action." See [POLICY-RCA.md](./POLICY-RCA.md) for root cause and correct process.

| Allowed tools (must exist on gateway) |
|--------------------------------------|
| `eka-target___search_medications` |
| `eka-target___search_protocols` |
| `eka-target___get_protocol_publishers` |
| `eka-target___search_pharmacology` |
| `maps-target___get_directions` |
| `maps-target___geocode_address` |
| `routing-target___get_route` |
| `get-hospitals-target___get_hospitals` |

*Do not assume tool names: the list must match the gateway schema. If `get_protocol_publishers` and `search_pharmacology` are not yet on the gateway, run the full sequence in [POLICY-RCA.md](./POLICY-RCA.md) (gateway → runtime scripts → add actions → policy script).*

**Default deny:** Any tool not in this list is denied. Adding a new target/tool requires updating the policy and re-running the setup script.

---

## Intended per-runtime restrictions (when using separate OAuth clients)

For **per-runtime** least privilege (Triage cannot call get_hospitals, etc.), you would:

1. Create **separate Cognito app clients** per runtime (Triage, Hospital Matcher, Routing) and configure each runtime with its own `client_id` / `client_secret`.
2. Add all three client IDs to the Gateway authorizer `allowedClients`.
3. Replace the single permit policy with **three permit policies**, one per principal (JWT `sub` = client identifier), each allowing only that runtime’s tools as in the table below.

| Agent / Runtime | Allowed tools (Gateway) | Not allowed |
|-----------------|-------------------------|-------------|
| **Triage** | `eka-target___search_medications`, `eka-target___search_protocols`, `eka-target___get_protocol_publishers`, `eka-target___search_pharmacology` | get_hospitals, get_route, get_directions |
| **Hospital Matcher** | `get-hospitals-target___get_hospitals`, `routing-target___get_route` | Eka tools, maps-target___get_directions (direct), submit_triage_result |
| **Routing** | `maps-target___get_directions`, `maps-target___geocode_address` | get_hospitals, Eka tools, get_route |

*(Note: `submit_triage_result` is an in-agent Converse tool, not a Gateway tool; Policy only applies to Gateway tool calls.)*

---

## How to apply or update Policy

1. **Prerequisites:** Gateway already created (`python3 scripts/setup_agentcore_gateway.py`) and gateway config in Secrets Manager.
2. **Run:**  
   `python3 scripts/setup_agentcore_policy.py`  
   This creates the policy engine (if missing), adds the allowlist Cedar policy, and attaches the engine to the Gateway in **ENFORCE** mode. By default the script uses **IGNORE_ALL_FINDINGS** so the policy (with action=target___tool) is accepted; at runtime the engine uses that format and the allowlist is enforced.  
   Use `--strict-validation` to use FAIL_ON_ANY_FINDINGS (policy create will then fail with "unrecognized action" because the validator expects ARN-prefixed actions).
3. **Dry-run:**  
   `python3 scripts/setup_agentcore_policy.py --dry-run`  
   Prints the Cedar statement and allowed actions without calling AWS.
4. **After adding a new Gateway target/tool:** Ensure the tool is registered on the gateway first (re-run `setup_agentcore_gateway.py`; for Eka, the script now updates an existing Eka target with all four tools). Then refresh Gateway env on runtimes: `enable_gateway_on_hospital_matcher_runtime.py`, `enable_gateway_on_routing_runtime.py`, and if needed `enable_eka_on_runtime.py` (see [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md)). Then add the corresponding `target___tool` to `ALLOWED_ACTIONS` in `scripts/setup_agentcore_policy.py` and re-run the policy script. The list must match the gateway schema; see [POLICY-RCA.md](./POLICY-RCA.md) for the full sequence (gateway → runtime scripts → policy).

---

## References

- **[POLICY-RCA.md](./POLICY-RCA.md)** – Root cause of "unrecognized action," correct Cedar format, and process for other policies (do not assume tool names).
- [Policy in AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html) – Control agent-to-tool interactions
- [Create a policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-policies.html) – Cedar structure, natural language authoring, schema constraints
- [Create a policy engine](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-engine.html)
- [Add policies to the Policy Engine](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/add-policies-to-engine.html)
- [Example policies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/example-policies.html) – Official Cedar examples (TargetName__tool_name; gateway ARN in resource only)
- [Update existing gateway with Policy Engine](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/update-existing-gateway-with-policy.html)
- [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) §4 – Guardrails and Policy
- [ROADMAP-NEXT.md](../ROADMAP-NEXT.md) Phase 2 – Policy (GA)
- [TODO.md](./TODO.md) – Policy implementation complete
