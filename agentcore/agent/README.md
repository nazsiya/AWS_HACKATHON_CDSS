# AgentCore agent – CDSS minimal runtime

This folder contains a **minimal deployable agent** and is the place to run the AgentCore CLI to create agents in AWS.

## Contents

- **`main.py`** – Entrypoint using Bedrock AgentCore SDK (`@app.entrypoint`). Handles hospitals-style and CDSS severity-assessment requests; falls back to a simple HTTP server if the SDK is not installed (local testing).
- **`requirements.txt`** – `bedrock-agentcore` for deployment.

## Create the agent in AWS

Agents are **not** created by Terraform. Use one of:

### Option A: Starter toolkit (recommended)

```bash
# From project root
pip install bedrock-agentcore-starter-toolkit bedrock-agentcore
cd agentcore/agent
agentcore create   # answer prompts (framework, name, region)
# Optional: keep or merge generated files with main.py
agentcore dev      # test locally
agentcore launch   # deploy to AWS → note Runtime ARN
```

### Option B: AWS Console

1. Build a deployment package: install dependencies for **Linux arm64** (see [AgentCore direct code deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html)), include `main.py` and deps, zip.
2. Upload zip to S3.
3. Bedrock → AgentCore → Host Agent → create agent from S3 → create endpoint → copy Runtime ARN.

Full steps: [docs/agentcore-create-agents-in-aws.md](../../docs/agentcore-create-agents-in-aws.md).

## After deploy

Set in `infrastructure/terraform.tfvars`:

- `use_agentcore = true`
- `agent_runtime_arn = "<Runtime ARN from deploy>"`

Then `terraform apply`. The CDSS API (`/api/v1/hospitals`, `/api/v1/triage` for CDSS severity assessment) will invoke this runtime when configured.

## References

- [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/develop-agents.html)
- [AgentCore Python SDK](https://github.com/aws/amazon-bedrock-agentcore-sdk-python)
