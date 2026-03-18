# Bedrock Setup for Local and Deployed API

AI chat and AI summary use **Amazon Bedrock**. For local runs, the API reads the Bedrock config from **AWS Secrets Manager** (no secrets in code). This guide gets Bedrock working when it's not configured.

---

## 1. Quick check: is Bedrock configured?

- **Local API:** Run the API, then open the **AI** page in the dashboard and send a message. If you see *"Bedrock is not configured. Set BEDROCK_CONFIG_SECRET_NAME..."* or *"Agent endpoint ready. Connect Bedrock for live responses."*, Bedrock is not in use.
- **Script:** With the API running:  
  `python scripts/verify_phase4_ai.py`  
  If POST /agent returns a real reply (not the fallback message), Bedrock is working.

---

## 2. What the backend needs

The backend expects:

1. **Secret name** in env or config: `BEDROCK_CONFIG_SECRET_NAME` (e.g. `cdss-dev/bedrock-config`).  
   - Local: set in repo root **.env**, or in **config.json** as `bedrock_config_secret_name` (used by `run_api_local.py`).
2. **Secret value** in **AWS Secrets Manager**: a JSON object with at least:
   - `model_id` — e.g. `apac.amazon.nova-lite-v1:0` (Nova Lite) or `anthropic.claude-3-haiku-20240307-v1:0` (Claude 3 Haiku).
   - `region` — e.g. `ap-south-1`.
3. **Model access** in the **Bedrock** console: the model you use must be **enabled** in that region.
4. **AWS credentials** so the process can call Secrets Manager and Bedrock (e.g. `aws configure` or env vars).

---

## 3. Steps to configure Bedrock (local)

### Step 1: Create or update the secret in AWS

1. Open **AWS Console** → **Secrets Manager** → region **ap-south-1** (or your chosen region).
2. Create a new secret (or edit existing):
   - **Secret type:** Other type of secret.
   - **Key/value:** Plaintext, and use JSON, for example:

```json
{
  "model_id": "apac.amazon.nova-lite-v1:0",
  "region": "ap-south-1"
}
```

   - For **Claude 3 Haiku** instead:

```json
{
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "region": "ap-south-1"
}
```

3. **Secret name:** Use the same name you reference in config (e.g. `cdss-dev/bedrock-config`). Note the full name (e.g. `cdss-dev/bedrock-config`).

### Step 2: Enable the model in Bedrock

1. **AWS Console** → **Amazon Bedrock** → **ap-south-1**.
2. In the left menu, open **Model access** (or **Foundation models**).
3. Find **Amazon Nova Lite** (or **Claude 3 Haiku**) and **Enable** it for that region.

### Step 3: Point the local API at the secret

**Option A — config.json (already used by run_api_local.py)**

In repo root **config.json**, set (or keep):

```json
"bedrock_config_secret_name": "cdss-dev/bedrock-config"
```

Use the exact secret name you created in Step 1.

**Option B — .env**

In repo root **.env**:

```env
BEDROCK_CONFIG_SECRET_NAME=cdss-dev/bedrock-config
AWS_REGION=ap-south-1
```

### Step 4: Ensure AWS credentials are available

From the same machine/terminal where you run the API:

- Run `aws configure` and set Access Key, Secret Key, and default region (e.g. `ap-south-1`), or
- Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` in the environment.

Then restart the local API (`python scripts/run_api_local.py`). The API will load the secret name from config or .env, fetch the secret from Secrets Manager, and call Bedrock with the given model and region.

---

## 4. Deployed (Lambda) API

Terraform sets **BEDROCK_CONFIG_SECRET_NAME** and the Lambda role has Bedrock and Secrets Manager permissions. Ensure:

- The same secret exists in Secrets Manager in the deployment region.
- The model is enabled in Bedrock in that region.
- No code changes are required; redeploy or update the secret value if you change model or region.

---

## 5. Troubleshooting

| Symptom | What to check |
|--------|----------------|
| "Bedrock is not configured" | `BEDROCK_CONFIG_SECRET_NAME` (or `bedrock_config_secret_name` in config.json) is set and the API was restarted after changing it. |
| "ValidationException" or "model not found" | Model is **enabled** in Bedrock console in the same region as in the secret. |
| "AccessDeniedException" | AWS credentials have permission to read the secret and to call `bedrock:InvokeModel` (or Converse) in that region. |
| Empty AI summary on Start consultation | Same as above; consultation summary uses the same Bedrock config. |

---

## 6. References

- **Pre-build checklist:** [PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md) (§1.2 Bedrock, §1.6 AgentCore).
- **Testing AI:** [TESTING_AI_SUMMARY_AND_ASSISTANCE.md](TESTING_AI_SUMMARY_AND_ASSISTANCE.md).
- **Run API locally:** `python scripts/run_api_local.py` (loads config.json from repo root).
