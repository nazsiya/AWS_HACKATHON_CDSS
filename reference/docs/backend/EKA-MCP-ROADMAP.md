# Eka Care MCP – what we have and what we can add

**References:** [Eka Care MCP Server](https://developer.eka.care/SDKs/EkaCare-MCP), [Supported Tools](https://developer.eka.care/ai-tools/mcp-server/supported-tools), [Get Started](https://developer.eka.care/user-guides/get-started).

---

## Implemented today

| Tool | Eka API | Purpose |
|------|---------|--------|
| **search_medications** | GET `/eka-mcp/medications/v1/search` | 500k+ Indian branded drugs; params: `drug_name`, `form`, `generic_names`, `volumes`. Returns name, generic_name, manufacturer_name, product_type. |
| **search_protocols** | POST `/eka-mcp/protocols/v1/search` | 180+ Indian treatment protocols (ICMR, RSSDI). Body: `queries[]` with `query`, `tag`, `publisher`. |
| **get_protocol_publishers** | GET `/eka-mcp/protocols/v1/publishers/all` | List of publisher names. Call before `search_protocols` to pass valid `publisher`. |
| **search_pharmacology** | GET `/eka-mcp/pharmacology/v1/search` | Generic (NFI) info: dose, indications, contraindications, pregnancy_category, adverse_effects. Params: `query`, optional `category`, `limit`, `exact_match`, `relevance_threshold`. |

All use Eka Connect auth (client_id + client_secret → login → access_token as Bearer). Wired in: Gateway Eka Lambda and `setup_agentcore_gateway.py` (all four tools). Triage currently uses `search_medications` and `search_protocols`; you can add `get_protocol_publishers` and `search_pharmacology` to triage tool config and agent for protocol filtering and dosing/safety.

---

## Can add next (same auth, same base URL)

### 1. **get_protocol_publishers** — implemented

- **API:** GET `/eka-mcp/protocols/v1/publishers/all`
- **Returns:** List of publisher names (e.g. ICMR, RSSDI).
- **Why:** Protocol search says "publisher … cannot be assumed unless … selected from output of get_protocol_publishers". Call this first, then pass valid `publisher` into `search_protocols`.
- **Doc:** [Get all Publishers](https://developer.eka.care/api-reference/knowledge-base/protocols/publishers)

### 2. **search_pharmacology** — implemented

- **API:** GET `/eka-mcp/pharmacology/v1/search`
- **Params:** `query` (drug name or compound e.g. "Rifampicin + Isoniazid"), optional `category`, `limit`, `exact_match`, `relevance_threshold`.
- **Returns:** Generic (NFI) info: dose, indications, contraindications, adverse_effects, pregnancy_category, storage, availability, etc. (National Formulary of India).
- **Why:** Dosing, safety, interactions for triage.
- **Doc:** [Get Generic (pharmacology) Information](https://developer.eka.care/api-reference/knowledge-base/medications/pharmacology)

### 3. **snomed_linking** (optional / later)

- **API:** GET `/eka-mcp/linking/v1/snomed` with `text_to_link` (array of terms e.g. ["dm2","htn"]).
- **Returns:** snomed_id, text, confidence per term.
- **Why:** Standardised codes; useful for coding/interop, less critical for initial triage.
- **Doc:** [SNOMED Linking](https://developer.eka.care/api-reference/knowledge-base/linking/snomed)

---

## Implementation checklist (for new tools)

1. **Eka Lambda:** Add function and handler branch; call `_eka_request` with correct method/path/params.
2. **Gateway setup:** Register new tool name and input schema for Eka target in `setup_agentcore_gateway.py`. If the Eka target already exists, the script will skip with "Eka target already exists"; to get new tools you may need to delete the eka target in AWS Console and re-run the setup, or use the API to update the target schema.
3. **Triage (optional):** Add tool spec in `tools.py`, gateway_client wrapper, and agent branch in `agent.py` so the model can call get_protocol_publishers and search_pharmacology.
4. **Runbook:** Extend EKA-VALIDATION-RUNBOOK E2/E3 with direct-invoke examples and response shape.
