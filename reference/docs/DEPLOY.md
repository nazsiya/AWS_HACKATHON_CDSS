# Deploy and configuration (why scripts, who runs them)

**Audience:** DevOps, frontend leads, hackathon evaluators.

---

## Why do we need scripts when secrets are in Secrets Manager and IAM can fetch them?

**Short answer:** IAM and Secrets Manager are fine. The gap is **what writes the gateway_config secret value** and **who sets runtime env vars**. Those are not done by Terraform today.

| What | Who has it / who can read it | Who creates or writes it today |
|------|------------------------------|---------------------------------|
| **api_config** | Lambdas have IAM to read it; Terraform writes the value | Terraform (`aws_secretsmanager_secret_version.api_config`) – so **no script** needed. |
| **gateway_config** | Route Lambda (and runtimes) have IAM to read it | **No Terraform resource** writes the value. The **value** (gateway_url, client_id, client_secret, token_endpoint, scope) only exists **after** the AgentCore Gateway is created and OAuth is set up. Terraform creates the **empty** secret; the script creates the Gateway via API and then writes the value. |
| **Runtime env vars** (GATEWAY_MCP_URL, etc.) | AgentCore runtimes use them to call the Gateway | Runtimes are created by **`agentcore deploy`** (CLI), not Terraform. Terraform has no resource for "AgentCore runtime env vars." The only way to set them is the Bedrock Control API **UpdateAgentRuntime**. The script does that. |

So we don't need scripts because Lambdas "can't" read secrets – they can. We need scripts because:

1. **Gateway + gateway_config value** – The Gateway resource is **not** in Terraform (we use a Python script + Bedrock API). The secret's **value** depends on Gateway URL and OAuth credentials that only exist after that API runs. So something that runs after Terraform must create the Gateway and write the secret.
2. **Runtime env** – Runtimes are managed by the AgentCore CLI/API, not Terraform. So something must call UpdateAgentRuntime to set Gateway env vars; today that's the script.

**What's missing for "no manual scripts" architecture**

- **Option A – Terraform creates the Gateway and populates the secret**  
  The AWS Terraform provider has **`aws_bedrockagentcore_gateway`** and **`aws_bedrockagentcore_gateway_target`**. We could move Gateway creation into Terraform and add an **`aws_secretsmanager_secret_version`** for gateway_config whose value is built from Terraform outputs (gateway URL + Cognito app client id/secret/token_endpoint). Then a single **`terraform apply`** would create the Gateway, targets, and the secret value; no setup script. Remaining work: authorizer config (CUSTOM_JWT with Cognito discovery URL and client id), and ensuring the same Cognito app client (or a dedicated "Gateway machine" client) is used so client_secret is in Terraform (e.g. `aws_cognito_user_pool_client` with client_secret).

- **Option B – Automate the script, don't remove it**  
  Keep the script but run it **inside CI/CD** after `terraform apply` (e.g. a pipeline step that runs `setup_agentcore_gateway.py` with AWS creds). Optionally, a **Lambda** that Terraform invokes (e.g. via `null_resource` + `local-exec` that invokes the Lambda, or a custom resource) could do the same work as the script (create Gateway, write secret). Then no human runs the script; apply or the pipeline does.

- **Runtime env (enable_gateway_on_*_runtime)**  
  Runtimes are still not in Terraform. After every **agentcore deploy** you must run the corresponding enable script so the runtime keeps Gateway (and Eka on Triage) env vars. See "After agentcore deploy" below.

**Recommendation:** For a cleaner architecture, implement **Option A** (Terraform Gateway + secret version) so `terraform apply` is sufficient for Gateway and gateway_config. CI/CD can be added later to automate agentcore deploy and the enable scripts.

---

## After agentcore deploy (required – do not skip)

**Whenever you run `agentcore deploy`** for Hospital Matcher, Triage, or Routing, you **must** run the corresponding enable script afterward. Deploy overwrites runtime env vars; without re-running the script, the runtime loses Gateway (and Eka on Triage) config and POST /hospitals, POST /route, or Eka triage will break.

| If you deployed | Run this (from project root) |
|------------------|------------------------------|
| Hospital Matcher | `python3 scripts/enable_gateway_on_hospital_matcher_runtime.py` |
| Triage | `python3 scripts/enable_eka_on_runtime.py` |
| Routing | `python3 scripts/enable_gateway_on_routing_runtime.py` |

---

## Why run scripts after Terraform?

- **Terraform** creates and configures: API Gateway, Lambdas (triage, hospital matcher, route, gateway_get_hospitals, gateway_maps, gateway_routing, gateway_eka), Secrets Manager **secret names** (e.g. `api-config`, `gateway-config`), IAM, RDS, etc. Lambdas get their config via **env vars** (e.g. `GATEWAY_CONFIG_SECRET_NAME`) and read secret values at runtime. So **Lambdas do not need any script to be run** for normal operation.

- The **AgentCore Gateway** and **gateway_config** secret **value** are not created by Terraform:
  - The **Gateway** (MCP + Cognito OAuth + targets like get_hospitals, maps, routing) is created by **`scripts/setup_agentcore_gateway.py`** using the Bedrock AgentCore Control API.
  - The **gateway_config** secret is created by Terraform as an **empty** secret; the **setup script** writes the Gateway URL, OAuth client_id/client_secret/token_endpoint/scope into it. So **POST /route** and any runtime that calls the Gateway need this secret to be **populated** by running the setup script once.

- **AgentCore runtimes** (Hospital Matcher, Triage, Routing) are created/updated by **`agentcore deploy`** (CLI), not Terraform. Their **environment variables** (e.g. Gateway URL, OAuth) are set via the Bedrock AgentCore Control API. Terraform has no provider that manages these runtimes. So we use a **script** that calls `UpdateAgentRuntime` to set the five Gateway env vars. The setup script does this by default so that after one run, both the Gateway and the runtimes are ready.

**Who runs the scripts when deploying to Lambda/EC2?**

- **First-time deploy (or new environment):** The person or CI pipeline that deploys the stack runs, in order:
  1. **`terraform apply`** – creates all AWS resources and secrets (with empty gateway_config).
  2. **`python3 scripts/setup_agentcore_gateway.py`** – creates the Gateway, populates gateway_config, and sets Gateway env vars on the Hospital Matcher and Routing runtimes.
  3. **`python3 scripts/setup_agentcore_policy.py`** – creates the policy engine and attaches it to the Gateway (tool allowlist, ENFORCE). Optional but recommended; see [POLICY-RUNBOOK.md](backend/POLICY-RUNBOOK.md).

- **Subsequent deploys:** If you only change Lambda code (e.g. Terraform apply again), you do **not** need to re-run the setup script unless you recreated the Gateway or the secret. If you **redeploy an AgentCore agent** (e.g. `agentcore deploy` for hospital_matcher_agent), that deploy can overwrite the runtime's env vars; **you must then re-run the corresponding enable script** (see "After agentcore deploy" above). So the "scripts" are either **one-time** (Gateway setup) or **required after every agentcore deploy** (re-apply env to that runtime).

---

## Deploy order (recommended)

| Step | Command | Purpose |
|------|---------|--------|
| 1 | `cd infrastructure && terraform apply` | Create API Gateway, Lambdas, secrets (api_config, gateway_config placeholder), RDS, etc. |
| 2 | `python3 scripts/setup_agentcore_gateway.py` | Create AgentCore Gateway, populate gateway_config, set Gateway env on Hospital Matcher and Routing runtimes. |
| 3 | `python3 scripts/setup_agentcore_policy.py` | Create policy engine and attach to Gateway (tool allowlist; ENFORCE). See [backend/POLICY-RUNBOOK.md](backend/POLICY-RUNBOOK.md). |
| 4 | **After every `agentcore deploy`** | Re-run the enable script for the agent you deployed (see "After agentcore deploy" above). Do not skip this or the runtime will lose Gateway/Eka env. |

**Getting API URL for frontend:** After step 1, the API URL is in the **api_config** secret. Run `eval $(python3 scripts/load_api_config.py --exports)` to set `API_URL` in your shell, or read the secret from your app (e.g. from a backend that exposes config). Terraform does not need to "run" anything else for Lambdas to work; they read secrets at runtime.

---

## Why POST /route or directions might fail after "it worked this afternoon"

- **gateway_config** is populated only by the setup script. If the secret was recreated (e.g. Terraform destroy/apply) or overwritten, it would be empty again and **POST /route** would return 503 (Gateway not configured) or 500 (e.g. token fetch failure).
- **Gateway OAuth** (Cognito) or **maps target** (gateway_maps Lambda) might be misconfigured or the Google Maps API key might be missing/invalid in the maps Lambda env.
- **Routing / Hospital Matcher runtimes** lose Gateway env vars after an **agentcore deploy**; re-run the enable script for the runtime you redeployed.

To fix: Re-run **`python3 scripts/setup_agentcore_gateway.py`** (and ensure `google_maps_api_key` is set in tfvars so the maps Lambda has the key). Then test **POST /route** again.

---

## Why the Google Maps URL / POST /route didn't work – and what we fixed

**What was going wrong**

1. **Route Lambda crashed with 500 (NameError)**  
   The Route Lambda used `logger` (e.g. `logger.warning`, `logger.info`, `logger.exception`) but **never defined it**. When the code tried to log (e.g. after loading gateway config or on success/failure), it raised `NameError` and the Lambda returned **500 Internal Server Error**. From the outside it looked like "POST /route / Google Maps URL not working."

2. **503 or no directions when gateway_config was missing**  
   The Route Lambda gets the Gateway URL and OAuth from the **gateway_config** secret in Secrets Manager. Terraform creates that secret but leaves its **value** empty; the value is filled only when you run **`python3 scripts/setup_agentcore_gateway.py`**. If gateway_config is empty, the Lambda returns **503** "Gateway not configured" and no directions_url. So even with correct code, POST /route would not return a Google Maps URL until the setup script had been run (and the maps Lambda had a valid Google Maps API key).

**What we did to fix it**

| Fix | Where | What |
|-----|--------|------|
| **Define the logger** | `infrastructure/route_lambda_src/lambda_handler.py` | Added `logger = logging.getLogger(__name__)` near the top so all `logger.*` calls work. After redeploying the Route Lambda (e.g. `terraform apply`), the 500 from NameError went away. |
| **Populate gateway_config** | One-time / after Terraform | Run **`python3 scripts/setup_agentcore_gateway.py`** so the gateway_config secret contains `gateway_url` and `client_info` (OAuth). Then the Route Lambda can call the Gateway and get directions. |
| **Google Maps API key** | Terraform / tfvars | Ensure **`google_maps_api_key`** is set in `terraform.tfvars` and Terraform is applied so the **gateway_maps** Lambda has the key. Without it, the Gateway can't call Google Routes API and directions_url may be missing or stub. |

After these, **POST /route** returns 200 with **distance_km**, **duration_minutes**, and **directions_url** (the Google Maps URL). The frontend can open that URL for turn-by-turn directions.

---

## Summary

| Question | Answer |
|----------|--------|
| Do Lambdas need scripts to run on each deploy? | No. Lambdas get config from Terraform (env) and read Secrets Manager at runtime. |
| Who runs the Gateway setup script? | Whoever does the first-time deploy, once per environment. |
| Who runs enable_gateway_on_*_runtime? | **You must run it after every agentcore deploy** for that agent, so the runtime keeps Gateway/Eka env. Do not skip. |
| Is this a good method? | Acceptable for now: Terraform owns infra; scripts fill the gap where Terraform doesn't manage the Gateway or runtime env. Option A (Terraform Gateway + secret) and CI/CD can be added later. |
