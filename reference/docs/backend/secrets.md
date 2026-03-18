# Secrets Manager – Created by Terraform

All of these secrets are **created and updated by Terraform** when you run `terraform apply`. They do not exist until then. Do not create them manually; use `cd infrastructure && terraform apply`.

---

## Secrets (name prefix: `{project_name}-{environment}` e.g. `emergency-medical-triage-dev`)

| Secret name | Description | Keys |
|-------------|-------------|------|
| **api-config** | API URL, Gateway Lambda ARNs, region, other secret names | `api_gateway_url`, `api_gateway_health_url`, `gateway_get_hospitals_lambda_arn`, `gateway_eka_lambda_arn`, `region`, `api_config_secret_name`, `gateway_config_secret_name`, `bedrock_config_secret_name`, `rds_config_secret_name`, `eka_config_secret_name` (null if no Eka key) |
| **gateway-config** | AgentCore Gateway OAuth and config (populated by **setup_agentcore_gateway.py**, not Terraform) | `gateway_url`, `gateway_id`, `region`, `client_info` (client_id, client_secret, token_endpoint, **scope** e.g. `emergency-triage-hospitals/invoke`, user_pool_id, domain_prefix), `target_name`, `lambda_arn`, optional `eka_target_name`, `maps_target_name`, `routing_target_name`, etc. **Route Lambda** reads this secret and uses `client_info.scope` when requesting an OAuth token. |
| **bedrock-config** | Bedrock region and model | `region`, `model_id` |
| **rds-config** | Aurora connection (IAM auth, no password) | `host`, `port`, `database`, `username`, `region` |
| **eka-config** | Eka Care API (only if `eka_api_key` set in tfvars) | `client_id`, `client_secret` (both required for Eka login; Lambda gets access_token via POST /connect-auth/v1/account/login). Legacy: `api_key` = client_id. |

---

## Using api-config (no Terraform output)

Scripts and curl can load config from the **api-config** secret after apply:

```bash
eval $(python3 scripts/load_api_config.py --exports)
curl -s "$API_URL"health
```

If the secret does not exist, the script exits with:  
`Secret '...' not found. Create it by running: cd infrastructure && terraform apply`

---

## Using gateway-config (OAuth for AgentCore runtimes)

The **gateway-config** secret is created by Terraform (empty); **setup_agentcore_gateway.py** fills it with Gateway URL and OAuth credentials. Never commit these to code.

If you already have a local `gateway_config.json` with `client_info`, run once (after `terraform apply`):

```bash
python3 scripts/setup_agentcore_gateway.py --save-to-secrets-only
```

That copies the full config to Secrets Manager and replaces the local file with a non-sensitive version. To export env vars for use on AgentCore runtimes or locally:

```bash
eval $(python3 scripts/load_gateway_config.py)
# Then set GATEWAY_MCP_URL, GATEWAY_CLIENT_ID, GATEWAY_CLIENT_SECRET, GATEWAY_TOKEN_ENDPOINT, GATEWAY_SCOPE on your runtime (Console) or use in shell
```

To get only the secret name: `python3 scripts/load_gateway_config.py --secret-name`

---

## Overriding the secret name

- **API_CONFIG_SECRET_NAME** – full secret name (e.g. `my-stack/api-config`)
- **GATEWAY_CONFIG_SECRET_NAME** – full secret name for gateway OAuth (default from api_config or `{NAME_PREFIX}/gateway-config`). **Route Lambda** uses this to get gateway_url and client_info (including scope) for calling the Gateway MCP endpoint.
- **NAME_PREFIX** – prefix only (default `emergency-medical-triage-dev`); script uses `{NAME_PREFIX}/api-config`
