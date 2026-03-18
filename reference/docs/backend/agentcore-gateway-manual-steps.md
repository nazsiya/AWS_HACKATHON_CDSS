# AgentCore Gateway: Manual Setup Steps

**Release and testing:** See [RELEASE-Gateway-Eka-Integration.md](./RELEASE-Gateway-Eka-Integration.md) and [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md).

The Gateway itself is not managed by Terraform. Terraform creates the **get_hospitals** and **gateway_eka** Lambdas and writes their ARNs (and the API URL) to the **api_config** secret so you don't need to rely on Terraform outputs.

## Prerequisites

- Terraform apply completed (creates Lambdas including gateway-get-hospitals, gateway-maps, gateway-routing, route)
- Python 3.10+ with `bedrock-agentcore-starter-toolkit` and `boto3` (use `python3` if `python` is not on PATH, e.g. macOS)
- AWS credentials configured (`aws configure` or env vars)
- Region: us-east-1 (or match `terraform.tfvars`)

## Step 1: Deploy Lambda via Terraform

```bash
cd infrastructure
terraform apply
```

Terraform creates the Lambdas and writes **api_config** to Secrets Manager (`{prefix}/api-config`) with `api_gateway_url`, `api_gateway_health_url`, `gateway_get_hospitals_lambda_arn`, `gateway_eka_lambda_arn`. Use the secret for scripts and curl (no need to run `terraform output`).

## Step 2: Install Setup Script Dependencies

```bash
pip install bedrock-agentcore-starter-toolkit boto3
```

## Step 3: Run Gateway Setup Script

No Terraform output needed: the script reads Lambda ARNs from the **api_config** secret if env vars are not set.

```bash
# Option A: load config from secret (boto3), then run setup
eval $(python3 scripts/load_api_config.py --exports)
python3 scripts/setup_agentcore_gateway.py

# Option B: run with no args; script reads api_config secret via boto3
python3 scripts/setup_agentcore_gateway.py
```

To pass ARNs explicitly: `GATEWAY_GET_HOSPITALS_LAMBDA_ARN`, `GATEWAY_EKA_LAMBDA_ARN`, `GATEWAY_MAPS_LAMBDA_ARN`, `GATEWAY_ROUTING_LAMBDA_ARN`, or first arg and `--eka <arn>`, `--maps <arn>`, `--routing <arn>`. Use `--gateway-id <id>` when reusing an existing Gateway.

The script will:

1. Create Cognito OAuth authorizer (or reuse when Gateway already exists: **syncs Gateway authorizer** to current OAuth so tokens from the saved client_info work)
2. Create MCP Gateway with Cognito auth (or reuse existing)
3. Add the get_hospitals Lambda as a target with tool schema
4. Optionally add Eka, Maps, and Routing targets
5. Add Lambda permission for the Gateway execution role
6. Save **full config (including client_info)** to **Secrets Manager** (`{prefix}/gateway-config`). Save only non-sensitive fields to `gateway_config.json` (no OAuth in code).

**Important:** When the Gateway already exists, the script updates the Gateway's authorizer to the current OAuth (discovery URL, allowed clients, scope). This avoids "Invalid Bearer token" when the Route Lambda (or other callers) use the client_info from the secret. MCP protocol version used by the Gateway is **2025-03-26** (Route Lambda sends this header).

## Step 4: Use the Gateway

- **MCP URL**: From Secrets Manager **gateway-config** secret → `gateway_url`, or from local `gateway_config.json` (non-sensitive only)
- **Auth**: From Secrets Manager **gateway-config** → `client_info` (client_id, client_secret, token_endpoint, **scope**). Use `eval $(python3 scripts/load_gateway_config.py)` to export env vars. The Route Lambda uses `client_info.scope` (e.g. `emergency-triage-hospitals/invoke`) when requesting a token.

### Step 4b: Wire Hospital Matcher agent to Gateway (optional)

To have the agent use the Gateway instead of in-agent synthetic data (and to get **per-hospital distance/directions** when patient location is provided), set these **environment variables on the AgentCore Runtime** for the Hospital Matcher:

- `GATEWAY_MCP_URL` = `gateway_url` from secret
- `GATEWAY_CLIENT_ID` = `client_info.client_id`
- `GATEWAY_CLIENT_SECRET` = `client_info.client_secret`
- `GATEWAY_TOKEN_ENDPOINT` = `client_info.token_endpoint`
- `GATEWAY_SCOPE` = `client_info.scope` or `bedrock-agentcore-gateway`

**Option A – Script (recommended):** From project root, run:

```bash
python3 scripts/enable_gateway_on_hospital_matcher_runtime.py
```

This reads the gateway-config secret and `agent_runtime_arn` from `infrastructure/terraform.tfvars` or from the **api_config** secret (Terraform writes it there when you apply). Use `--dry-run` to print without updating. **Normally you don’t need this:** running `python3 scripts/setup_agentcore_gateway.py` (without `--skip-runtime-env`) automatically sets these env vars on the Hospital Matcher runtime when `agent_runtime_arn` is in api_config. Re-run this script only after you redeploy the Hospital Matcher agent (`agentcore deploy`), because deploy can overwrite runtime env.

**Option B – Console:** Get values with `eval $(python3 scripts/load_gateway_config.py)` and add the five variables in AWS Console → Bedrock → AgentCore → Runtimes → your Hospital Matcher runtime → configuration/environment.

After this, POST /hospitals with `patient_location_lat` and `patient_location_lon` can return hospitals with `distance_km`, `duration_minutes`, and `directions_url` (from the Routing agent via Gateway). Without these env vars, the runtime returns synthetic stub hospitals (no lat/lon) and no route info.

### Step 4c: Wire Triage to Eka (optional)

**If triage uses Converse (use_agentcore_triage = false):**  
The Triage Lambda loads Gateway config from the **gateway-config** secret (GATEWAY_CONFIG_SECRET_NAME). Ensure `python3 scripts/setup_agentcore_gateway.py` has been run so the secret contains `gateway_url` and `client_info`. Then POST /triage will use Eka when the model calls search_indian_medications / search_treatment_protocols.

**If triage uses AgentCore (use_agentcore_triage = true):**  
The Lambda invokes the **AgentCore Runtime** (triage_agent); the Converse path and Lambda gateway_config are not used. To use Eka, set the same Gateway **env vars on the AgentCore Runtime**:

- **Option A – Script (recommended):** From project root, run `python3 scripts/enable_eka_on_runtime.py`. This reads the gateway-config secret and triage_agent_runtime_arn from infrastructure/terraform.tfvars and sets GATEWAY_MCP_URL, GATEWAY_CLIENT_ID, GATEWAY_CLIENT_SECRET, GATEWAY_TOKEN_ENDPOINT, and GATEWAY_SCOPE on the triage runtime. Use --dry-run to print vars without updating. If the script cannot find the ARN, use `--tfvars path/to/infrastructure/terraform.tfvars`. **IAM:** Your user/role needs `bedrock-agentcore:GetAgentRuntime` and `bedrock-agentcore:UpdateAgentRuntime`; if you get AccessDeniedException, add those actions to your IAM policy (see [runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)).

- **Option B – Console:** Get values with `eval $(python3 scripts/load_gateway_config.py)` and add the five variables in AWS Console → Bedrock → AgentCore → Runtimes → triage runtime → configuration/environment.

Ensure the Eka target is added to the Gateway (setup script with Eka). Then the triage agent on the runtime can call Eka tools.

## Lambda Handler Format (Reference)

The Gateway invokes the Lambda with:

- **Event**: `{ "severity": "high", "limit": 3 }` (tool input props)
- **Context**: `client_context.custom["bedrockAgentCoreToolName"]` = `TARGET___get_hospitals`
- **Response**: `{ "hospitals": [...], "safety_disclaimer": "..." }`

Strip the `TARGET___` prefix to identify the tool when multiple tools share one Lambda.

## Troubleshooting

| Issue | Action |
|-------|--------|
| "Lambda permission already exists" | Safe to ignore; permission was added previously |
| "Could not add Lambda permission" | Manually add resource policy: allow `bedrock-agentcore.amazonaws.com` or Gateway execution role to invoke the Lambda |
| Toolkit creates default Lambda | Use boto3 `create_gateway_target` (as in the script) with your Lambda ARN and tool schema; do not use `target_payload=None` |
| Tool not found in MCP | Verify target name; full tool name is `{target_name}___get_hospitals` |

---

## See also

- [RELEASE-Gateway-Eka-Integration.md](./RELEASE-Gateway-Eka-Integration.md) – Release notes and configuration reference  
- [TESTING-Gateway-Eka.md](./TESTING-Gateway-Eka.md) – Unit, integration, and API testing steps
