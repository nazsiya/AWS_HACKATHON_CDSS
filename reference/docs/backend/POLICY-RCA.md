# AgentCore Policy – Root Cause Analysis and Correct Process

**Purpose:** Document why policy creation showed "unrecognized action" errors, what was done wrong, and the correct format and process for future policies.

---

## 1. Correct Cedar format (verified working)

The policy that **finally worked** uses this structure:

```cedar
permit(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"eka-target___search_medications",
        AgentCore::Action::"eka-target___search_protocols",
        AgentCore::Action::"maps-target___get_directions",
        AgentCore::Action::"maps-target___geocode_address",
        AgentCore::Action::"routing-target___get_route",
        AgentCore::Action::"get-hospitals-target___get_hospitals"
    ],
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:197542484821:gateway/emergency-triage-hospitals-1bdyfrfmui"
);
```

**Rules:**

| Item | Correct | Wrong |
|------|--------|--------|
| **Action format** | `target___tool` (triple underscore; MCP tool name) | `target__tool`, or `arn:...gateway/...__target__tool` in the action |
| **Action scope** | Only tools that **exist in the gateway schema** | Assuming tool names that are not registered on the gateway |
| **Resource** | `AgentCore::Gateway::"<full gateway ARN>"` | Gateway ARN inside the action string |

---

## 2. Root cause of "unrecognized action" errors

"Unrecognized action" can mean **two different things**:

1. **Wrong action format** – e.g. using ARN in the action, or double underscore instead of triple. The validator/schema expects a specific shape.
2. **Action not in schema** – The action string is well-formed, but **that tool is not registered on the gateway**. The Cedar schema is generated from the gateway’s tool manifest; if a tool was never added to the gateway (or was added under a different target/tool name), it will not be in the schema.

In our case, **both** applied:

- We tried many **formats** (plain `target___tool`, `target__tool`, `gateway_arn__target__tool`, `gateway_arn__target___tool`). The validator often suggested an ARN-prefixed form, which was misleading because the **working** policy uses plain `target___tool`.
- We **assumed** tool names. We included `eka-target___get_protocol_publishers` and `eka-target___search_pharmacology` in `ALLOWED_ACTIONS` because they exist in our codebase (Lambda, gateway setup script, docs). On **this** gateway, those two tools were **not** registered (or not in the schema). So the real failure for those two was **“tool does not exist in schema”**, not format.

---

## 3. What was done wrong (RCA)

| Mistake | What happened | Why it was wrong |
|--------|----------------|-------------------|
| **Assumed tool names** | `ALLOWED_ACTIONS` was populated from code/docs (e.g. all 4 EKA tools: search_medications, search_protocols, get_protocol_publishers, search_pharmacology) without verifying they exist on the gateway. | Policy schema is derived from the **gateway’s** tool manifest. If a tool is not on the gateway, it is not in the schema and will always be “unrecognized.” |
| **Treated all errors as format issues** | Every “unrecognized action” was interpreted as “wrong Cedar format” and we kept changing between `target__tool`, `target___tool`, ARN-prefixed, etc. | For `get_protocol_publishers` and `search_pharmacology`, the real cause was **tool not in schema**. No format change would fix that. |
| **Relied on “did you mean” for format** | The console “did you mean” suggested an ARN-prefixed action, so we switched to ARN-prefixed actions. | The working policy uses **no** ARN in the action. The suggestion was misleading or referred to a different context. |
| **No single source of truth for “what’s on the gateway”** | The list of allowed tools lived only in the policy script and was not derived from the gateway or schema. | The only authoritative list is the set of tools actually registered on the gateway. Policy must be a subset of that. |

---

## 4. Correct process for other policies

When defining or updating an AgentCore Gateway policy:

1. **Know what’s on the gateway**
   - The Cedar schema is generated from the gateway’s tool manifest after the policy engine is attached.
   - Only tools that are **registered on the gateway** (target + tool) appear in the schema. Do not assume names from code, Lambda, or docs; confirm which targets/tools this gateway actually has (e.g. from gateway config, setup script output, or console).

2. **Use the correct Cedar format**
   - **Actions:** `target___tool` (triple underscore). This is the MCP tool name ([Gateway tool naming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html)). Do **not** put the gateway ARN in the action.
   - **Resource:** `AgentCore::Gateway::"<gateway ARN>"`.

3. **Restrict the allowlist to schema-only**
   - In `ALLOWED_ACTIONS` (or equivalent), list **only** tools that exist on this gateway. If you add a tool that is not in the schema, you will get “unrecognized action” until you either register that tool on the gateway or remove it from the policy.

4. **Interpret “unrecognized action” correctly**
   - First check: **Is this tool actually on the gateway?** If not, remove it from the policy or add it to the gateway.
   - Second: Use **exactly** `target___tool` for the action; do not use ARN in the action.

5. **Validation mode**
   - If the policy uses only schema-existing tools and the correct format, validation may still report findings on some gateways. Use `IGNORE_ALL_FINDINGS` when necessary so the policy is created and enforced; runtime uses `target___tool`.

---

## 5. Reference: working allowlist for this gateway

For gateway `emergency-triage-hospitals-1bdyfrfmui`, the tools that **exist in the schema** and are allowed by the working policy are:

- `eka-target___search_medications`
- `eka-target___search_protocols`
- `maps-target___get_directions`
- `maps-target___geocode_address`
- `routing-target___get_route`
- `get-hospitals-target___get_hospitals`

Not in this gateway’s schema (and therefore must not appear in the policy on this gateway):

- `eka-target___get_protocol_publishers`
- `eka-target___search_pharmacology`

**Why they were missing:** The gateway setup script (`setup_agentcore_gateway.py`) only **created** the Eka target with all four tools; when the target **already existed** (ConflictException), it did not **update** the target to add the extra tools (unlike the Maps target, which has an update path). So if the Eka target was created earlier—e.g. with only two tools or by an older script—it stayed that way. The script was updated to call `update_gateway_target` for the Eka target when it already exists.

**To add the two tools end-to-end**, run these steps in order:

1. **Update the gateway** so the Eka target has all four tools:
   ```bash
   python3 scripts/setup_agentcore_gateway.py
   ```
2. **Refresh Gateway env on runtimes** (see [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md)) so agents can use the gateway and any new tools:
   ```bash
   python3 scripts/enable_gateway_on_hospital_matcher_runtime.py
   python3 scripts/enable_gateway_on_routing_runtime.py
   ```
   If Triage uses Eka tools, also run:
   ```bash
   python3 scripts/enable_eka_on_runtime.py
   ```
3. **Add the two actions** to `ALLOWED_ACTIONS` in `scripts/setup_agentcore_policy.py`:
   - `eka-target___get_protocol_publishers`
   - `eka-target___search_pharmacology`
4. **Re-run the policy script** so the allowlist includes them:
   ```bash
   python3 scripts/setup_agentcore_policy.py
   ```

---

## 6. Related docs

- [POLICY-RUNBOOK.md](./POLICY-RUNBOOK.md) – How to apply/update policy and optional per-runtime restrictions  
- [Gateway tool naming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html) – `target___tool` pattern  
- [Example policies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/example-policies.html) – Official Cedar examples (format may differ from our gateway; use `target___tool` and resource = gateway ARN as above)
