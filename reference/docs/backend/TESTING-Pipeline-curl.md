# Pipeline testing with curl (Triage → Hospitals → Route)

**Purpose:** Test the full pipeline (POST /triage → POST /hospitals → POST /route) with curl. All three POST endpoints require **RMP auth** (Cognito Id token in `Authorization: Bearer <token>`).

---

## 1. Get API base URL and a valid token

All secrets (Cognito test user email and password) are stored in **AWS Secrets Manager** and read via boto3. No passwords on the command line.

**One-time setup:** Put the test RMP user credentials in Terraform so they are stored in Secrets Manager:

1. Create a test user in Cognito (AWS Console → Cognito → your User Pool → Users → Create user, or use `aws cognito-idp admin-create-user`).
2. In `infrastructure/terraform.tfvars` add (use the same email/password as that user):

   ```hcl
   rmp_test_email    = "rmp@example.com"
   rmp_test_password = "YourActualPassword"
   ```

   (`terraform.tfvars` is gitignored so these are not committed; Terraform writes them to Secrets Manager.)

3. Run `cd infrastructure && terraform apply`. Terraform stores these in the secret `{prefix}/rmp-test-credentials`; the script reads them via boto3.

**Get base URL and token:**

From the **project root** (directory that contains `infrastructure/`):

```bash
# API base URL (run from project root)
cd infrastructure && terraform output -raw api_gateway_url && cd ..
# Example: https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev/

# Id token (reads email/password from Secrets Manager via boto3; no secrets on CLI)
# Use python3 if python is not available (e.g. on macOS)
TOKEN=$(python3 scripts/get_rmp_token.py)
```

If `get_rmp_token.py` fails with "Secret ... rmp-test-credentials not found", set `rmp_test_email` and `rmp_test_password` in `terraform.tfvars` and run `terraform apply` (see one-time setup above). If Cognito returns "User does not exist", create the user in the Cognito User Pool first.

---

## 2. Health (no auth)

```bash
BASE="https://YOUR_API_URL/dev"   # trailing slash optional
curl -s "${BASE}/health"
```

---

## 3. Pipeline: Triage → Hospitals → Route

Set your base URL once (from `terraform output -raw api_gateway_url`). Token comes from Secrets Manager via the script (no password on CLI).

**Run these from the project root** (the directory that contains both `scripts/` and `infrastructure/`), not from inside `infrastructure/`:

```bash
cd /Users/vickramkarthickr/Work/AI_Hackathon_Triage

BASE="https://YOUR_API_URL/dev"   # get from: cd infrastructure && terraform output -raw api_gateway_url
# Use python3 if python is not available
TOKEN=$(python3 scripts/get_rmp_token.py)
```

### Step A – POST /triage

```bash
curl -s -X POST "${BASE}/triage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "symptoms": ["chest pain", "shortness of breath"],
    "vitals": { "heart_rate": 110, "blood_pressure_systolic": 140 },
    "age_years": 55,
    "sex": "M"
  }'
```

**Expected:** JSON with `severity` (e.g. `high` or `critical`), `recommendations`, `confidence`, `session_id`. Note `severity` for the next step.

### Step B – POST /hospitals (use severity from triage)

```bash
# Use the severity from triage output (e.g. "high")
curl -s -X POST "${BASE}/hospitals" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "severity": "high",
    "recommendations": ["Emergency department"],
    "limit": 3
  }'
```

**With patient location** (so Hospital Matcher can call Routing agent for distance/directions):

```bash
curl -s -X POST "${BASE}/hospitals" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "severity": "high",
    "recommendations": ["Emergency department"],
    "limit": 3,
    "patient_location_lat": 12.9716,
    "patient_location_lon": 77.5946
  }'
```

**Expected:** JSON with `hospitals` array (name, match_score, match_reasons, lat/lon, etc.). If Routing agent and Gateway are wired, entries may include distance/directions when patient location is provided.

### Step C – POST /route (directions between two points)

```bash
# By coordinates
curl -s -X POST "${BASE}/route" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "origin":      { "lat": 12.9716, "lon": 77.5946 },
    "destination": { "lat": 13.0827, "lon": 80.2707 }
  }'
```

**Or by address** (requires Google Maps API key configured):

```bash
curl -s -X POST "${BASE}/route" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "origin":      { "address": "MG Road, Bangalore" },
    "destination": { "address": "Chennai Central, Chennai" }
  }'
```

**Expected:** JSON with `distance_km`, `duration_minutes`, `directions_url`. If Google Maps is not configured, you may get `stub: true` and null values.

---

## 4. One-liner summary (after setting BASE and TOKEN)

```bash
# 1. Triage
curl -s -X POST "${BASE}/triage" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"symptoms":["chest pain"],"vitals":{"heart_rate":100},"age_years":55,"sex":"M"}'

# 2. Hospitals (use severity from above, e.g. "high")
curl -s -X POST "${BASE}/hospitals" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"severity":"high","recommendations":["Emergency department"],"limit":3,"patient_location_lat":12.97,"patient_location_lon":77.59}'

# 3. Route
curl -s -X POST "${BASE}/route" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"origin":{"lat":12.97,"lon":77.59},"destination":{"lat":13.08,"lon":80.27}}'
```

---

## 5. Troubleshooting

| Response | Cause |
|----------|--------|
| **401 Unauthorized** | Missing or invalid/invalidated Id token. Get a fresh token (step 1). |
| **403 Forbidden** | Token present but authorizer rejected (e.g. wrong User Pool). Check Cognito config. |
| **Route returns stub / null** | Google Maps API key not set or Maps Lambda not configured. See [GOOGLE-MAPS-ACCOUNT-SETUP.md](../infrastructure/GOOGLE-MAPS-ACCOUNT-SETUP.md). |
| **Hospitals without distance** | Hospital Matcher may not be calling Routing agent; ensure Gateway env vars are set on the Hospital Matcher runtime and `routing-target___get_route` is registered. |
| **Hospitals show stub-1, stub-2, no directions_url** | The Hospital Matcher **AgentCore runtime** does not have Gateway env vars set, so it uses in-agent synthetic data (no lat/lon) and get_route returns stub. Run `python3 scripts/enable_gateway_on_hospital_matcher_runtime.py` from project root (see [agentcore-gateway-manual-steps.md](./agentcore-gateway-manual-steps.md) Step 4b). |
