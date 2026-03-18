# Eka validation runbook (E1–E5)

**Purpose:** Verify Eka Care integration (Indian drugs, treatment protocols): config, direct Lambda test, response shape, and whether we get real data or stubs.

---

## E1. Config and secret check

### 1.1 Terraform: is Eka configured?

- **Variables:** `eka_api_key` (Eka **Client ID**) and `eka_client_secret` (Eka **Client Secret**) in `infrastructure/variables.tf`. Eka requires both: the Lambda calls **POST /connect-auth/v1/account/login** to get an **access_token**, then uses that as Bearer for medications/protocols APIs ([Eka Get Started](https://developer.eka.care/user-guides/get-started)). Without `client_secret`, the Lambda falls back to using client_id as Bearer (legacy) and Eka may return **403 Forbidden**.
- **Where to set:** `infrastructure/terraform.tfvars` (e.g. `eka_api_key = "your-client-id"`, `eka_client_secret = "your-client-secret"`) or `-var=...`. Get both from [Eka Console](https://console.eka.care). Do not commit secrets.
- **Check after apply:**
  ```bash
  cd infrastructure
  terraform output eka_config_secret_name
  ```
  - If **empty** or **null**: Eka is not configured; Lambda will return stub data.
  - If **non-empty** (e.g. `emergency-medical-triage-dev/eka-config`): Secret exists. Ensure the secret contains both `client_id` and `client_secret` for login (or you will get 403).

### 1.2 Eka Lambda environment

- **Lambda:** `gateway_eka` (see `infrastructure/gateway_eka.tf`).
- **Env vars:**
  - `EKA_API_BASE` = `https://api.eka.care` (default).
  - `EKA_CONFIG_SECRET_NAME` = set only when `eka_api_key != ""` (Terraform sets it to the secret name).
- **IAM:** Lambda role can read the Eka secret only when `var.eka_api_key != ""` (policy `gateway_eka_secrets` is count-based).
- **Check deployed Lambda:**
  ```bash
  aws lambda get-function-configuration --function-name <gateway-eka-function-name> --query 'Environment.Variables'
  ```
  - If `EKA_CONFIG_SECRET_NAME` is `""` or missing → stub mode.
  - If it equals the secret name from `terraform output eka_config_secret_name` → real Eka when secret has valid `api_key`/`client_id`.

### 1.3 Gateway target

- Eka is a **second** Gateway target (optional). Setup is done by **scripts/setup_agentcore_gateway.py** with `--eka` or when the script reads `gateway_eka_lambda_arn` from the **api_config** secret and adds the Eka target.
- **api_config** secret (from Terraform) contains `gateway_eka_lambda_arn` and `eka_config_secret_name` (null if Eka not set).
- **gateway-config** secret (filled by setup script) contains `eka_target_name` (e.g. `eka-target`) when Eka was added.
- **To add or refresh Eka target:** Run `python3 scripts/setup_agentcore_gateway.py` (it reads api_config; use `--eka <lambda_arn>` to override). See [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md).

**E1 checklist:** eka_api_key (Client ID) and eka_client_secret set in tfvars → terraform output eka_config_secret_name non-null → secret has client_id + client_secret → Lambda has EKA_CONFIG_SECRET_NAME → Gateway setup run with Eka target.

---

## E2. Direct Eka Lambda test

Invoke the **deployed** Eka Lambda with test payloads to see stub vs real response.

### 2.1 Get Lambda name

```bash
cd infrastructure
terraform output -raw gateway_eka_lambda_arn
# Or from api_config:
eval $(python3 scripts/load_api_config.py --exports)
# Then use the ARN; for invoke you need the function name, e.g.:
aws lambda list-functions --query "Functions[?contains(FunctionName,'gateway-eka')].FunctionName" --output text
```

### 2.2 Test search_medications

**Payload:** `{"drug_name": "Paracetamol"}` (optional: `form`, `generic_names`, `volumes`).

```bash
aws lambda invoke \
  --function-name <gateway-eka-function-name> \
  --payload '{"drug_name":"Paracetamol"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/eka-med-out.json
cat /tmp/eka-med-out.json | jq .
```

**Stub response** (Eka not configured or secret missing/invalid):

- Contains `"message": "Eka not configured; stub data."`
- `medications` is a fixed list (e.g. "Paracetamol 500mg Tablet", "ORS Sachet", manufacturer "Stub").

**Real response** (Eka API key valid):

- No `"message": "Eka not configured; stub data."`
- `medications` from Eka API (Indian branded drugs; real names/manufacturers).

### 2.3 Test search_protocols

**Payload:** `{"tool": "search_protocols", "queries": [{"query": "fever", "tag": "", "publisher": ""}]}`. The `tool` key is used when invoking the Lambda directly (no Gateway context).

```bash
aws lambda invoke \
  --function-name <gateway-eka-function-name> \
  --payload '{"tool":"search_protocols","queries":[{"query":"fever"}]}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/eka-prot-out.json
cat /tmp/eka-prot-out.json | jq .
```

**Stub response:**

- Contains `"message": "Eka not configured; stub data."`
- `protocols` is a fixed stub (e.g. one item: conditions "Acute fever", author "ICMR").

**Real response:**

- No stub message; `protocols` from Eka API (Indian treatment protocols, e.g. ICMR, RSSDI).

### 2.4 Local stub test (no AWS)

From project root, with **no** Eka secret name so handler returns stub:

```bash
cd infrastructure/gateway_eka_lambda_src
EKA_CONFIG_SECRET_NAME= python3 -c "
from lambda_handler import handler
class Ctx:
    class client_context:
        custom = {'bedrockAgentCoreToolName': 'eka-target___search_medications'}
out = handler({'drug_name': 'Paracetamol'}, Ctx())
assert 'medications' in out
assert 'message' in out and 'stub' in out.get('message','').lower()
print('OK: stub medications')
"
```

See also [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) §2.4.

---

## E3. Response shape and stub vs real

### 3.1 search_medications

| Key | Type | Stub | Real (Eka API) |
|-----|------|------|-----------------|
| `medications` | array | Fixed list of 2 items | List from Eka `/eka-mcp/medications/v1/search` |
| `message` | string | `"Eka not configured; stub data."` | Absent |
| Each medication | object | `name`, `generic_name`, `manufacturer_name`, `product_type` | Same shape; real brands/manufacturers |

**Stub example:**

```json
{
  "medications": [
    {
      "name": "Paracetamol 500mg Tablet",
      "generic_name": "Paracetamol",
      "manufacturer_name": "Stub",
      "product_type": "Tablet"
    },
    {
      "name": "ORS Sachet",
      "generic_name": "Oral Rehydration Salts",
      "manufacturer_name": "Stub",
      "product_type": "Sachet"
    }
  ],
  "message": "Eka not configured; stub data."
}
```

**When stub is returned:** `EKA_CONFIG_SECRET_NAME` is empty (Terraform `eka_api_key` not set), or secret missing, or Secrets Manager/API error (Lambda logs warning and returns empty list; wrapper may still add stub message in code path where secret name is empty).

### 3.2 search_protocols

| Key | Type | Stub | Real (Eka API) |
|-----|------|------|-----------------|
| `protocols` | array | Fixed list of 1 item | List from Eka `/eka-mcp/protocols/v1/search` |
| `message` | string | `"Eka not configured; stub data."` | Absent |
| Each protocol | object | `conditions`, `author`, `source_url`, `type` | Same shape; real protocols (ICMR, RSSDI, etc.) |

**Stub example:**

```json
{
  "protocols": [
    {
      "conditions": ["Acute fever"],
      "author": "ICMR",
      "source_url": null,
      "type": "pdf"
    }
  ],
  "message": "Eka not configured; stub data."
}
```

**Request shape (for direct invoke):** `queries` is a list of objects with optional `query`, `tag`, `publisher` (up to 5 used). When Eka API fails or returns non-JSON, Lambda returns `{"protocols": []}` and logs a warning (no stub message in that path; stub message only when `EKA_CONFIG_SECRET_NAME` is empty).

### 3.3 How to decide “real” vs “stub”

- **Stub:** Response contains the exact string `"Eka not configured; stub data."` (in `message`) or medications/protocols match the fixed stub items above.
- **Real:** No such message; medications/protocols vary by query and look like production Eka data (Indian drug names, real publishers).

---

## E4. Triage flow that uses Eka

- **Prereq:** Triage Lambda has Gateway env vars set; Gateway has Eka target; Eka Lambda has valid EKA_CONFIG_SECRET_NAME (and secret has valid key).
- **Test:** POST /triage with a payload that may encourage the model to call Eka (e.g. symptoms mentioning a drug name or “suitable medication”, or “treatment protocol”).
- **Verify:** In CloudWatch logs for the Triage Lambda (and Gateway/Eka Lambda), confirm that the Gateway was called and Eka tool was invoked (e.g. `eka-target___search_medications` or `eka-target___search_protocols`) and that the tool result was returned. Model behaviour is non-deterministic; you may need to try a few prompts.
- See [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) §3.2 and §3.5.

---

## E5. Decide “useful” bar

- **If Eka returns real data:** Document 2–3 sample queries (medications + protocols) and add them to [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) or this runbook; use in CI/manual regression.
- **If only stub:** Document “Eka stub mode” (this runbook E1–E3) and the steps to enable real Eka: set `eka_api_key` in tfvars, apply, run Gateway setup with Eka target, obtain key from [Eka Care console](https://console.eka.care) if needed.

---

## References

| Doc | Purpose |
|-----|--------|
| [Eka Get Started](https://developer.eka.care/user-guides/get-started) | Eka auth: Client ID + Client Secret → login API → access_token as Bearer |
| [Eka Client Login](https://developer.eka.care/api-reference/authorization/client-login) | POST /connect-auth/v1/account/login |
| [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) | Gateway + Eka integration tests, local stub test |
| [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md) | Gateway setup; use `python3` for scripts |
| [secrets.md](./secrets.md) | api_config, eka-config secret keys |
| [ROADMAP-after-AC4.md](./ROADMAP-after-AC4.md) | E1–E5 in roadmap |
