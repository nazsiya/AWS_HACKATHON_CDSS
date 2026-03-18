# CDSS Gateway Configuration

This folder holds the **gateway configuration** used to connect the CDSS frontend apps (Doctor Dashboard, Patient Portal) to the AWS backend.

## Files

| File | Purpose |
|------|--------|
| `gateway-config.json` | Single source of truth: API Gateway URLs, WebSocket URL, Cognito IDs, CloudFront URLs, and frontend env mappings. |
| `gateway-config.schema.json` | JSON Schema for validating `gateway-config.json`. |

## Populating from Terraform

After `terraform apply` in `infrastructure/`, run:

```bash
cd infrastructure
terraform output -json > ../config/terraform-outputs.json
```

Then update `gateway-config.json` (or use a script) with:

| gateway-config.json path | Terraform output key |
|-------------------------|----------------------|
| `apiGateway.baseUrl` | `api_gateway_url.value` |
| `apiGateway.cdssApiBase` | `api_gateway_cdss_url.value` |
| `apiGateway.healthUrl` | `api_gateway_health_url.value` |
| `websocket.url` | `websocket_url.value` |
| `cognito.userPoolId` | `cognito_user_pool_id.value` |
| `cognito.staffClientId` | `cognito_staff_client_id.value` |
| `cognito.patientClientId` | `cognito_patient_client_id.value` |
| `cloudFront.staffAppUrl` | `staff_app_cf_url.value` (prepend `https://`) |
| `cloudFront.patientPortalUrl` | `patient_portal_cf_url.value` (prepend `https://`) |

Region is set in `infrastructure/terraform.tfvars` (`aws_region`) and should match `cognito.region` and `aws.region`.

## Using in frontend apps

- **Doctor Dashboard**: Use `frontend.doctorDashboard` values as `VITE_*` env vars (e.g. in `.env` or CI).
- **Patient Dashboard**: Use `frontend.patientDashboard` (same structure; `VITE_COGNITO_CLIENT_ID` is the patient client).

Example `.env` for doctor-dashboard (from this config):

```env
VITE_API_URL=https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev
VITE_WS_URL=wss://jcw3vemil9.execute-api.ap-south-1.amazonaws.com/dev
VITE_COGNITO_USER_POOL_ID=ap-south-1_0eRSiDzbY
VITE_COGNITO_CLIENT_ID=15hk1uremldsor79jkc7cr866v
VITE_COGNITO_REGION=ap-south-1
VITE_USE_MOCK=false
```

## API routes (backend)

The REST API Gateway exposes:

- `GET /health` — Health check (no auth).
- `GET|POST|PUT|DELETE /api/{proxy+}` — CDSS API (Cognito auth); e.g. `/api/v1/patients`, `/api/v1/triage`.
- `GET /dashboard` — Dashboard summary (Cognito auth).
- `POST /agent` — Agent/conversation (Cognito auth).

WebSocket: connect to `websocket.url`; when authorizer is enabled, pass Cognito JWT as query param `token`.

## Security

- Do not commit secrets to `gateway-config.json`. It only contains URLs and Cognito app client IDs (public in SPAs).
- Keep `terraform.tfvars` (and any `.tfvars` with `db_password` etc.) out of version control or use a secrets manager.
