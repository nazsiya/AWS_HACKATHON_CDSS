# Resolve Bedrock Failures (AI Assistant Unavailable)

When the AI Assistant shows **"AI is temporarily unavailable"** (or the backend returns a generic error), the cause is usually one of: **model not enabled**, **wrong region**, or **IAM**. Follow these steps in order.

**Fallback:** The backend automatically tries **Amazon Nova Lite** (`apac.amazon.nova-lite-v1:0`) if the configured model (e.g. Claude) fails. Ensure Nova Lite is enabled in your Bedrock region for best resilience.

---

## 1. See the real error

The backend now includes a short exception hint in the reply when Bedrock fails (e.g. `ValidationException: Model ... not found`).

- **Redeploy the backend** (Lambda) so the change is live, e.g. from `infrastructure/` run:
  ```bash
  terraform apply
  ```
- In the **Doctor Dashboard**, open a patient and use the **AI Assistant**; send any message.
- If Bedrock is still failing, the reply will include a hint such as:
  - **`ValidationException: Model ... not found`** → wrong or disabled model (go to step 2).
  - **`AccessDeniedException`** → IAM/permissions (go to step 4).
  - **`ResourceNotFoundException`** → wrong region or secret name (go to steps 2–3 and 5).

You can also check **CloudWatch Logs** for the Lambda that handles `/agent` (e.g. the `api` or `supervisor` function) to see the full stack trace.

---

## 2. Enable the model in Bedrock

The model referenced in your config **must be enabled** in your AWS account and region.

1. In **AWS Console**, open **Amazon Bedrock** in the **same region** as your Lambda (e.g. **ap-south-1**).
2. Go to **Model access** (or **Foundation models**) in the left menu.
3. Find the model you use (see step 3 for where it’s set) and click **Enable**.
4. Wait until the model shows as **Enabled**.

**Suggested models for ap-south-1 (Mumbai):**

- **Amazon Nova Lite**: `apac.amazon.nova-lite-v1:0` — good default for ap-south-1.
- **Claude**: If you use Claude, ensure the exact model ID (e.g. `anthropic.claude-3-haiku-20240307-v1:0`) is available and enabled in **ap-south-1**; model IDs and availability vary by region.

---

## 3. Set the correct secret (Secrets Manager)

The Lambda reads Bedrock config from **AWS Secrets Manager**. The secret name is in the Lambda env **`BEDROCK_CONFIG_SECRET_NAME`** (Terraform sets this to e.g. `cdss-dev/bedrock-config`).

1. In **AWS Console** → **Secrets Manager**, open the secret with that name.
2. Edit the secret value and set it to **JSON** like:
   ```json
   {
     "model_id": "apac.amazon.nova-lite-v1:0",
     "region": "ap-south-1"
   }
   ```
   - Use the **exact** `model_id` from the Bedrock console for the model you enabled (e.g. for Nova Lite in ap-south-1: `apac.amazon.nova-lite-v1:0`).
   - Set **`region`** to the region where the model is enabled (e.g. `ap-south-1`).

**If you use Terraform:** The secret is defined in `infrastructure/secrets.tf` and populated from **`var.bedrock_model_id`** and **`var.aws_region`**. Set `bedrock_model_id` in `terraform.tfvars` to the model you enabled, then run `terraform apply` to update the secret:

```hcl
# terraform.tfvars (ap-south-1 example)
bedrock_model_id = "apac.amazon.nova-lite-v1:0"
```

---

## 4. Fix Lambda IAM

The Lambda execution role must be allowed to call Bedrock and to read the secret.

1. In **IAM**, open the **role** used by the Lambda that handles **`/agent`** (and any handler that calls Bedrock).
2. Ensure the role has:
   - **`bedrock:InvokeModel`** (and optionally **`bedrock:InvokeModelWithResponseStream`**) for the Bedrock model.
   - **`secretsmanager:GetSecretValue`** on the secret named in **`BEDROCK_CONFIG_SECRET_NAME`**.

**In this project:** Permissions are defined in:

- **`infrastructure/lambda_iam.tf`** — allows `GetSecretValue` on the RDS and Bedrock config secrets.
- **`infrastructure/bedrock.tf`** — defines **`aws_iam_policy.bedrock_invoke`** with:
  - A **broad statement** (`Resource = "*"`) for `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` so Converse works in all regions and with inference profiles (fixes **AccessDeniedException** when the model ARN doesn’t match region-specific resources).
  - Explicit region ARNs for foundation models and inference profiles in ap-south-1, us-east-1, us-east-2, us-west-2.
- **`infrastructure/modules/lambda/main.tf`** — attaches the Bedrock policy when **`attach_bedrock_policy = true`** (set in **`infrastructure/main.tf`** for the API Lambda).

If you see **AccessDeniedException** when calling Converse, run **`terraform apply`** so the updated Bedrock policy (with `Resource = "*"`) is applied to the Lambda role.

---

## 5. Region and model ID

- The **`region`** in the secret must be a region where the model is **enabled** (e.g. **ap-south-1**).
- **Model IDs** can differ by region; use the ID shown in the Bedrock console for that region (e.g. `apac.amazon.nova-lite-v1:0` for Nova Lite in ap-south-1).

---

## Quick checklist

| Check | Where |
|-------|--------|
| Model enabled in Bedrock | AWS Console → Bedrock → Model access (correct region) |
| Secret has correct `model_id` and `region` | Secrets Manager → secret named in `BEDROCK_CONFIG_SECRET_NAME` |
| Lambda has `BEDROCK_CONFIG_SECRET_NAME` | Lambda env (Terraform sets it) |
| Lambda role has Bedrock + Secrets Manager permissions | `infrastructure/lambda_iam.tf`, `bedrock.tf`, `modules/lambda/main.tf` |

After completing these steps, trigger the AI Assistant again. If it still fails, the **hint in the reply** plus **CloudWatch Logs** for the Lambda will show the exact Bedrock error.

More context: **`docs/DEBUGGING_API_AND_DATABASE.md`** (section 9 – AI Assistant and Bedrock).

---

## Verify AI is working

1. **Redeploy** after any IAM or secret change: from `infrastructure/` run **`terraform apply -auto-approve`**.
2. In the **Doctor Dashboard**, open a patient and send a message in the **AI Assistant** (e.g. “Tell me about this patient”). You should get a natural-language reply, or a clear error hint (e.g. AccessDeniedException, model not found).
3. **Start consultation** should return **200** and create a visit; if the DB is unreachable you’ll see **503** with “Database temporarily unavailable” instead of a generic 500.
4. Optional: run **`python scripts/verify_models_and_endpoints.py --skip-endpoints`** (with `PYTHONPATH=src` and AWS credentials) to check Bedrock config and optionally invoke the model.
