# Release: Gateway & Eka Integration

**Release scope:** AgentCore Gateway wiring (A, B, C) and Eka Care integration for Triage  
**Branch:** `feature/Agentcore-implementation`  
**Date:** February 2026

---

## 1. Overview

This release adds **Amazon Bedrock AgentCore Gateway** integration and **Eka Care** (Indian drugs and treatment protocols) to the Emergency Medical Triage backend.

| Capability | Description |
|------------|-------------|
| **Hospital Matcher → Gateway** | Hospital Matcher agent can use the Gateway MCP `get_hospitals` tool instead of in-agent synthetic data when Gateway credentials are configured. |
| **Eka as Gateway target** | A new Lambda exposes Eka Care APIs as Gateway tools: `search_medications` and `search_protocols` (Indian drugs, ICMR/RSSDI protocols). |
| **Triage → Eka** | The Triage Converse flow can call Eka tools via the Gateway when Gateway credentials are set on the Triage Lambda, enabling drug and protocol lookups during assessment. |

All additions are **backward compatible**: existing behaviour is unchanged when Gateway or Eka are not configured.

---

## 2. What Changed

### 2.1 A – Hospital Matcher agent wired to Gateway

- **New:** `agentcore/agent/gateway_client.py`  
  - Sync OAuth client-credentials token + JSON-RPC `tools/call` to the Gateway MCP URL.  
  - `get_hospitals_via_gateway(severity, limit)` calls tool `get-hospitals-target___get_hospitals`.
- **Updated:** `agentcore/agent/hospital_matcher_agent.py`  
  - The single tool implementation calls `get_hospitals_via_gateway()` when `GATEWAY_MCP_URL` (and OAuth env vars) are set; otherwise uses in-agent `get_synthetic_hospitals()`.
- **Config:** Set on the **AgentCore Runtime** (Console or deployment):  
  `GATEWAY_MCP_URL`, `GATEWAY_CLIENT_ID`, `GATEWAY_CLIENT_SECRET`, `GATEWAY_TOKEN_ENDPOINT`, optional `GATEWAY_SCOPE`.  
  Values come from `gateway_config.json` after running the Gateway setup script.

### 2.2 B – Eka as Gateway target

- **New:** `infrastructure/gateway_eka.tf`  
  - Lambda `gateway_eka` (Python 3.12), IAM with optional Secrets Manager read for `{prefix}/eka-config`.  
  - Env `EKA_CONFIG_SECRET_NAME` set when `eka_api_key` is non-empty in Terraform.
- **New:** `infrastructure/gateway_eka_lambda_src/lambda_handler.py`  
  - Gateway target implementing:
    - **search_medications** – GET Eka `/eka-mcp/medications/v1/search` (drug_name, form, generic_names, volumes).  
    - **search_protocols** – POST Eka `/eka-mcp/protocols/v1/search` (queries: query, tag, publisher).  
  - Uses Bearer token from Secrets Manager (`api_key` or `client_id`). Returns stub data when the secret is not configured.
- **Updated:** `scripts/setup_agentcore_gateway.py`  
  - `--eka <lambda_arn>` (or `GATEWAY_EKA_LAMBDA_ARN`) adds a second Gateway target `eka-target` with the two tool schemas.  
  - Lambda permission uses a distinct statement id (`AllowAgentCoreGatewayInvokeEka`) to avoid conflicts.

### 2.3 C – Triage agent wired to Eka via Gateway

- **New:** `src/triage/core/gateway_client.py`  
  - Sync Gateway MCP client for Lambda (OAuth + `tools/call`).  
  - `search_medications(...)` and `search_protocols(queries)` call `eka-target___search_medications` and `eka-target___search_protocols`.
- **Updated:** `src/triage/core/tools.py`  
  - New schemas: `SEARCH_MEDICATIONS_SCHEMA`, `SEARCH_PROTOCOLS_SCHEMA`.  
  - `get_triage_tool_config_with_eka()` – when Gateway is configured (env vars set), adds tools `search_indian_medications` and `search_treatment_protocols` and uses `toolChoice: any`; otherwise returns the existing single-tool config.
- **Updated:** `src/triage/core/agent.py`  
  - `_assess_via_converse()` uses `get_triage_tool_config_with_eka()`.  
  - Multi-round loop: on `tool_use` for the Eka tools, calls the Gateway and appends tool results to the conversation until the model calls `submit_triage_result` or the loop limit is reached.
- **Config:** Set on the **Triage Lambda**: same `GATEWAY_*` env vars as above. Eka target must be added to the Gateway (setup script with `--eka`).

### 2.4 Infrastructure and docs

- **Updated:** `infrastructure/triage.tf` – build triggers for `tools.py` and `gateway_client.py`.  
- **Updated:** `docs/backend/agentcore-gateway-manual-steps.md` – Step 3 (Eka in setup), Step 4b (Hospital Matcher Gateway), Step 4c (Triage Eka).  
- **Updated:** `docs/backend/implementation-history.md` – Gateway status and next steps.  
- **Updated:** `docs/backend/TODO.md` – Phase 1 (A, B, C) marked done.

---

## 3. Components Summary

| Component | Role |
|-----------|------|
| **Gateway (MCP)** | Single Gateway; Cognito OAuth; targets: `get-hospitals-target` (Lambda), optional `eka-target` (Lambda). |
| **get_hospitals Lambda** | Returns synthetic Indian hospitals; tool name `get-hospitals-target___get_hospitals`. |
| **gateway_eka Lambda** | Calls Eka APIs when secret present; tools `eka-target___search_medications`, `eka-target___search_protocols`. |
| **Hospital Matcher agent** | Runtime agent; one tool that uses Gateway when `GATEWAY_*` set, else synthetic. |
| **Triage Lambda** | Converse API; when `GATEWAY_*` set, exposes Eka tools and runs multi-round tool loop. |

---

## 4. Configuration Reference

### 4.1 Gateway setup (one-time)

1. **Terraform:** `terraform apply` (creates Lambdas and writes **api_config** to Secrets Manager with `api_gateway_url`, `api_gateway_health_url`, `gateway_get_hospitals_lambda_arn`, `gateway_eka_lambda_arn`).
2. **Script:** Run `python scripts/setup_agentcore_gateway.py` with no args; it reads Lambda ARNs from the **api_config** secret via boto3. Or run `eval $(python scripts/load_api_config.py --exports)` then run the script.

### 4.2 Hospital Matcher → Gateway

On the **AgentCore Runtime** (e.g. Console or deployment config), set from `gateway_config.json` and `client_info`:

- `GATEWAY_MCP_URL`  
- `GATEWAY_CLIENT_ID`  
- `GATEWAY_CLIENT_SECRET`  
- `GATEWAY_TOKEN_ENDPOINT`  
- `GATEWAY_SCOPE` (optional; default `bedrock-agentcore-gateway`)

Redeploy the agent: `cd agentcore/agent && agentcore deploy`.

### 4.3 Triage → Eka

On the **Triage Lambda**, set the same `GATEWAY_*` variables. Ensure the Eka target is on the Gateway (setup with `--eka`). No code change required; behaviour is driven by env.

### 4.4 Eka API (optional)

- Store Eka API key in Terraform: `eka_api_key` in `terraform.tfvars` (sensitive) or `-var="eka_api_key=..."`.  
- Terraform creates `{prefix}/eka-config` secret with `api_key` and `client_id`.  
- Gateway Eka Lambda reads this secret; without it, the Lambda returns stub medication/protocol data.

---

## 5. Testing

**Quick local checks (no AWS):**
PYTHONPATH=src python3 -c "
import os
for k in ('GATEWAY_MCP_URL','GATEWAY_CLIENT_ID','GATEWAY_CLIENT_SECRET','GATEWAY_TOKEN_ENDPOINT'):
    os.environ.pop(k, None)
from triage.core.tools import get_triage_tool_config_with_eka
c = get_triage_tool_config_with_eka()
assert len(c['tools']) == 1
print('OK: no Gateway -> single tool')
os.environ['GATEWAY_MCP_URL']='x'
os.environ['GATEWAY_CLIENT_ID']='x'
os.environ['GATEWAY_CLIENT_SECRET']='x'
os.environ['GATEWAY_TOKEN_ENDPOINT']='x'
c = get_triage_tool_config_with_eka()
assert any(t['toolSpec']['name']=='search_indian_medications' for t in c['tools'])
print('OK: with Gateway -> Eka tools')
"

# Eka Lambda stub (from Lambda source dir)
cd infrastructure/gateway_eka_lambda_src && EKA_CONFIG_SECRET_NAME= python3 -c "
from lambda_handler import handler
class Ctx:
    class client_context: custom = {'bedrockAgentCoreToolName': 'eka-target___search_medications'}
assert 'medications' in handler({'drug_name': 'Paracetamol'}, Ctx())
print('OK: Eka Lambda stub')
"
```

Full steps, sample payloads, and integration tests: **[TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md)**.

---

## 6. Troubleshooting

| Symptom | Check |
|--------|--------|
| Hospital Matcher still returns synthetic data | Runtime env: `GATEWAY_MCP_URL` and OAuth vars set? Redeploy agent after setting. |
| Triage never calls Eka tools | Triage Lambda env: `GATEWAY_*` set? Eka target added (`--eka`)? Model may not always call tools. |
| Eka Lambda returns stub data | Secret `{prefix}/eka-config` exists and has `api_key`? Lambda env `EKA_CONFIG_SECRET_NAME` correct? |
| Gateway 403 / auth errors | `client_info` in `gateway_config.json`; token endpoint and scope correct; Cognito app client not disabled. |
| Tool not found in MCP | Full tool name is `{target_name}___{tool_name}` (e.g. `eka-target___search_medications`). |
| Script can't find Lambda ARNs | Ensure **api_config** secret exists (created by Terraform). Run `eval $(python scripts/load_api_config.py --exports)` or set `API_CONFIG_SECRET_NAME`. |

---

## 7. References

- [AgentCore Gateway: Manual Setup Steps](./agentcore-gateway-manual-steps.md)  
- [AgentCore Implementation Plan](./agentcore-implementation-plan.md)  
- [Implementation History](./implementation-history.md)  
- [Backend TODO](./TODO.md)  
- [Testing Gateway & Eka](./TESTING-Gateway-Eka.md)
