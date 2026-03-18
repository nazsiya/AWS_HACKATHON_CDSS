# AgentCore Gateway: Manual Setup Steps

This document describes manual setup for the **Bedrock AgentCore Gateway** used by CDSS (hospital-matching and CDSS severity-assessment flows). The Gateway exposes Lambda/MCP tools to AgentCore agents, satisfying [requirements.md](./requirements.md) Req 8 (MCP for agent-to-agent communication) and aligning with the CDSS MCP adapter pattern in the [implementation plan](./implementation-plan.md).

The Gateway itself is not managed by Terraform because the bedrock-agentcore-starter-toolkit (or Control Plane API) creates Cognito, Gateway, and target resources. Terraform manages the **Lambda(s)** that the Gateway invokes (e.g. `get_hospitals`, or CDSS tools such as hospital data, OT status, ABDM stub).

## Prerequisites

- Terraform apply completed (creates the Lambda used by the Gateway, e.g. `gateway-get-hospitals` or CDSS gateway Lambda)
- Python 3.10+ with `boto3`
- AWS credentials configured (`aws configure` or env vars)
- **Region:** For CDSS in **ap-south-1**, the script uses the Lambda ARN’s region (ap-south-1) so the Gateway is created in ap-south-1. To force a different gateway region (e.g. us-east-1), set `AGENTCORE_GATEWAY_REGION`.

## Step 1: Deploy Lambda via Terraform

```bash
cd infrastructure
terraform apply
```

Note the output for the Lambda ARN used by the Gateway, e.g.:

```
gateway_get_hospitals_lambda_arn = "arn:aws:lambda:ap-south-1:ACCOUNT:function:cdss-gateway-get-hospitals-dev"
```

For CDSS, the Gateway may invoke a single Lambda that implements multiple tools (e.g. `get_hospitals`, `get_ot_status`, `get_abdm_record`) aligned with [implementation plan](./implementation-plan.md) MCP adapter; tool names and schemas should match what agents expect.

## Step 2: Install Setup Script Dependencies

```bash
pip install bedrock-agentcore-starter-toolkit boto3
```

## Step 3: Run Gateway Setup Script

Run from the **project root** (where `scripts/` lives), not from `infrastructure/`:

```bash
# From project root
cd /path/to/AI_Hackathon_CDSS

# Option A: Pass Lambda ARN as argument (get it from Terraform)
python scripts/setup_agentcore_gateway.py $(cd infrastructure && terraform output -raw gateway_get_hospitals_lambda_arn)

# Option B: Use env var
export GATEWAY_GET_HOSPITALS_LAMBDA_ARN=$(cd infrastructure && terraform output -raw gateway_get_hospitals_lambda_arn)
python scripts/setup_agentcore_gateway.py
```

PowerShell (from project root):

```powershell
cd D:\AI_Hackathon_CDSS
$arn = (cd infrastructure; terraform output -raw gateway_get_hospitals_lambda_arn)
python scripts/setup_agentcore_gateway.py $arn
```

The script will:

1. Create IAM role for the Gateway (or reuse existing)
2. Create MCP Gateway with NONE auth (or reuse existing if name conflicts)
3. Print that Lambda target must be added in Console (API supports only MCP targets)
4. Add Lambda permission for the Gateway (in the Lambda’s region)
5. Save `gateway_config.json` with `gateway_url`, `gateway_id`, `region`, `client_info`

**Gateway name:** `cdss-gateway-{region}` (e.g. **cdss-gateway-ap-south-1** for India). The **gateway ID** (e.g. `cdss-gateway-ap-south-1-xxxxxxxxxx`) is in `gateway_config.json` after the script runs.

## Step 4: Add Lambda target (Console)

The Control Plane API only supports MCP targets. Add your Lambda as a target in the Console:

1. **Bedrock** → **AgentCore** → **Gateways**
2. Open the gateway (e.g. **cdss-gateway-ap-south-1**)
3. **Targets** → **Add target** → choose your Lambda when the option is available

## Step 5: Use the Gateway

- **MCP URL**: From `gateway_config.json` → `gateway_url`
- **Tool name**: `{target_name}___{tool_name}` (e.g. `get-hospitals-target___get_hospitals`, or CDSS tool names as configured)
- **Auth**: Use `client_info` (client_id, client_secret, token_endpoint, scope) for OAuth client-credentials flow

## After gateway is created (next steps)

1. **Add Lambda target (Console)**  
   Bedrock → AgentCore → Gateways → [your gateway] → Targets → Add target → attach the gateway-tools Lambda when the option is available.

2. **Test the hospitals API**  
   Call `POST <api-base>/api/v1/hospitals` with body `{"severity": "high", "limit": 5}`. You should get a response (stub or AgentCore). Check CloudWatch for `HospitalMatcher source=... duration_ms=...`.

3. **Proceed to AC-2 (All 5 Agents + Observability)**  
   See [agentcore-implementation-plan.md](./agentcore-implementation-plan.md): extend Gateway Lambda with tools for Patient, Surgery, Resource, Scheduling, Engagement agents; enable tracing with Patient_ID/Doctor_ID in log metadata (CDSS.mdc).

## Lambda Handler Format (Reference)

The Gateway invokes the Lambda with:

- **Event**: Tool input props (e.g. `{ "severity": "high", "limit": 3 }` for get_hospitals, `{ "patient_id": "PT-1001" }` for get_patient, or CDSS-specific params for surgery/schedule/engagement tools)
- **Context**: `client_context.custom["bedrockAgentCoreToolName"]` = `TARGET___tool_name`
- **Response**: JSON matching the tool’s declared schema (e.g. `{ "hospitals": [...], "safety_disclaimer": "..." }`). For CDSS clinical tools, include safety disclaimers per [.cursor/rules/CDSS.mdc](../.cursor/rules/CDSS.mdc).

Strip the `TARGET___` prefix to identify the tool when multiple tools share one Lambda.

## Troubleshooting

| Issue | Action |
|-------|--------|
| "Lambda permission already exists" | Safe to ignore; permission was added previously |
| "Could not add Lambda permission" | Manually add resource policy: allow `bedrock-agentcore.amazonaws.com` or Gateway execution role to invoke the Lambda |
| Toolkit creates default Lambda | Use boto3 `create_gateway_target` (as in the script) with your Lambda ARN and tool schema; do not use `target_payload=None` |
| Tool not found in MCP | Verify target name; full tool name is `{target_name}___get_hospitals` |
