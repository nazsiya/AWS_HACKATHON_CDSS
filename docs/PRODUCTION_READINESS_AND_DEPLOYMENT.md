# Production Readiness and Deployment Guide

This guide makes the CDSS project **production-ready** and **deployable**, and fixes **frontend–backend alignment** so the dashboard and API behave consistently in production.

---

## 1. Alignment Issues (What's Not Aligning Today)

| Issue | Current state | Production-ready fix |
|-------|----------------|----------------------|
| **GET /health** | In production, `/health` is served by a **separate** Node.js Lambda that returns only `{ status, service }`. The frontend **ApiHealthBanner** expects `body.database === 'connected'`. | Route **GET /health** to the **CDSS router Lambda** (same as local) so the response includes `database: "connected" \| "unavailable"`. See §4.1. |
| **Swagger UI / OpenAPI** | Lambda package is built from `src/` only; `docs/swagger.yaml` is **not** in the zip. So **GET /api/docs** and **GET /docs/swagger.yaml** return 404 in production. | Either bundle `docs/` into the Lambda zip and set `CDSS_REPO_ROOT`, or document that Swagger is **local-only** and use a separate docs host. See §4.2. |
| **Cognito required** | `api_require_cognito` defaults to **true**. Production API returns **401** if the frontend does not send a valid Cognito JWT. | For production with auth: set **VITE_COGNITO_*** in frontend build and ensure login flow sends the token. For early production without auth: set `api_require_cognito = false` in Terraform. See §4.3. |
| **Frontend API URL at build time** | Vite bakes **VITE_API_URL** into the bundle at **build** time. If you build without the correct URL, the deployed app calls the wrong backend. | Build the frontend with the **exact** production API base URL (e.g. `https://xxx.execute-api.ap-south-1.amazonaws.com/dev`). See §5.2. |
| **Schedule / Appointments / Tasks** | Schedule, Appointments, and Dashboard tasks pages were using **mock data only**. | ✅ **FIXED** — `Schedule.jsx`, `Appointments.jsx`, `Dashboard.jsx` now call `GET /api/v1/schedule`, `GET /api/v1/appointments`, `GET /api/v1/tasks` respectively. Falls back to mock data only when `VITE_USE_MOCK=true`. |
| **CORS** | API Gateway CORS is set to `'*'` for OPTIONS. **Gateway Responses** add CORS headers to all 4xx/5xx (e.g. 401 from Cognito) so the browser does not block with "access control checks". For production you may restrict **Access-Control-Allow-Origin** to the CloudFront domain. | Optional: parameterize allowed origins in Terraform and pass the CloudFront or custom domain. |

---

## 1.1 New API Endpoints Added

| Endpoint | Handler | Purpose |
|----------|---------|----------|
| `GET /api/v1/appointments` | `appointments.py` | List appointments from visits table joined with patients/doctors |
| `POST /api/v1/appointments` | `appointments.py` | Create a new appointment |
| `GET /api/v1/tasks` | `tasks.py` | Aggregate pending clinical tasks (surgeries, reminders, follow-ups) |
| `POST /api/ai/prescription` | `ai.py` | AI-suggested prescription from patient history |
| `POST /api/ai/adherence` | `ai.py` | Medication adherence analysis |
| `POST /api/ai/engagement` | `ai.py` | Patient engagement scoring |
| `POST /api/ai/resources` | `ai.py` | Health education resources for diagnosis |

---

## 2. Production Readiness Checklist

Use this before going live.

### 2.1 Backend (API + Lambda)

- [ ] **Health endpoint** — GET /health returns `{ service, status, database }` (see §4.1).
- [ ] **Secrets** — `RDS_CONFIG_SECRET_NAME` and `BEDROCK_CONFIG_SECRET_NAME` exist in Secrets Manager and are set in Lambda env (Terraform does this).
- [ ] **Database** — Aurora is reachable from Lambda (VPC + security groups if Lambda is in VPC), or use RDS Proxy; migrations applied.
- [ ] **Cognito** — If using auth: User Pool and App Client(s) exist; frontend has correct `VITE_COGNITO_*`. If not: `api_require_cognito = false`.
- [ ] **Swagger** — Decide: bundle docs in Lambda (§4.2) or keep Swagger local-only.
- [ ] **Region** — All resources in the same region (e.g. `ap-south-1`); PROJECT_REFERENCE.md and config match.

### 2.2 Frontend

- [ ] **Build env** — `VITE_API_URL` set to production API base URL (no trailing slash) at **build** time.
- [ ] **VITE_USE_MOCK** — `false` for production build.
- [ ] **Cognito** — If using auth: `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`, `VITE_COGNITO_REGION` set at build time.
- [ ] **SPA fallback** — Production server (S3 + CloudFront or similar) serves `index.html` for client-side routes (e.g. `/patients`, `/ai`).

### 2.3 Database

- [ ] **Migrations** — `python -m cdss.db.migrations.run` (or equivalent) applied to production DB.
- [ ] **Seed (optional)** — Seed data for dev/staging; avoid seeding PHI in prod.
- [ ] **Backups** — RDS automated backups and retention configured.

### 2.4 Security and Compliance

- [ ] **TLS** — API Gateway and CloudFront use HTTPS.
- [ ] **Secrets** — No secrets in `.env` committed; use Secrets Manager / Parameter Store / build-time env only.
- [ ] **RBAC** — Patient role cannot list all patients; enforced in router (see IMPLEMENTATION_STATUS_AND_COMPLETION.md).
- [ ] **Audit** — Clinically relevant actions logged (audit_log); review coverage.

---

## 3. Deployment Steps (High Level)

1. **Infrastructure** — Apply Terraform (VPC, RDS, Lambda, API Gateway, S3, CloudFront, Cognito, secrets). Apply health-endpoint fix (§4.1).
2. **Secrets** — Populate RDS and Bedrock secrets in Secrets Manager (Terraform creates names; you set values).
3. **Database** — Run migrations (and optional seed) against Aurora (via bastion tunnel or from a Lambda/runner with network access).
4. **Backend** — Lambda is deployed by Terraform from `src/`. Update code → re-apply or use CI to build zip and update function code.
5. **Frontend** — Build with production `VITE_API_URL` (and Cognito vars); upload build output to S3; invalidate CloudFront if used.
6. **Smoke test** — GET /health (expect `database` in body); GET /dashboard; login (if Cognito); open dashboard and load patients.

---

## 4. Fixes to Apply

### 4.1 Route GET /health to CDSS Lambda (Align with Frontend)

The frontend expects **GET /health** to return `{ service, status, database? }`. Today in production a separate health Lambda returns only `{ status, service }`.

**Option A (recommended):** Point API Gateway **GET /health** to the **CDSS router Lambda** (same as `/dashboard` and `/agent`). Then the same Python router serves health and returns `database: "connected" | "unavailable"`.

- **Applied in this repo:** In `infrastructure/api_gateway.tf`, the GET /health integration uses `module.cdss_lambda.invoke_arn`, and the router (`src/cdss/api/handlers/router.py`) treats any path ending with `/health` (e.g. `/dev/health`) as the health endpoint so the same contract works with API Gateway stages. After `terraform apply`, GET /health returns `{ service, status, database }` in production.
- The standalone `aws_lambda_function.health` Lambda is still present (e.g. for other consumers); API Gateway no longer calls it for /health.

**Option B:** Keep the current health Lambda and extend its response to include a `database` field by calling the same DB check (e.g. via a shared layer or a simple RDS connection check). This requires changing the Node.js health Lambda and giving it VPC/security group if it must reach RDS.

Apply **Option A** so production matches local behavior and the ApiHealthBanner works without code changes.

### 4.2 Swagger in Production (Optional)

- **Option A:** Bundle `docs/` (at least `docs/swagger.yaml`) in the Lambda zip. In Terraform (e.g. `modules/lambda`), add `docs` to the packaged paths and set env `CDSS_REPO_ROOT` to the directory that contains `docs/` inside the deployment package (e.g. `/var/task` if docs are at the root of the zip). Then the router's `_repo_root()` can find and serve the spec.
- **Option B:** Do not serve Swagger from the production API. Document that **GET /api/docs** and **GET /docs/swagger.yaml** are for **local development only**. Use a separate docs host or static site if you need public API docs in production.

### 4.3 Cognito: Production vs No-Auth

- **With Cognito:** Set `api_require_cognito = true` (default). Ensure:
  - Frontend build has `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`, `VITE_COGNITO_REGION`.
  - Login flow stores and sends the JWT (e.g. `Authorization: Bearer <token>`).
  - API Gateway authorizer is configured (Terraform already ties it to the Cognito User Pool).
- **Without Cognito (e.g. first deploy / internal only):** Set `api_require_cognito = false` in Terraform so API Gateway does not require a JWT. Frontend can still call the API without tokens. Re-enable Cognito when ready.

---

## 5. Frontend Build and Deploy

### 5.1 Build for Production

From the **doctor-dashboard** app (and similarly for patient-dashboard if used):

```powershell
cd d:\AI_Hackathon_CDSS\frontend\apps\doctor-dashboard

# Set production API URL (replace with your API Gateway URL and stage)
$env:VITE_API_URL = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev"
$env:VITE_USE_MOCK = "false"

# If using Cognito
$env:VITE_COGNITO_USER_POOL_ID = "ap-south-1_xxxxx"
$env:VITE_COGNITO_CLIENT_ID = "your-client-id"
$env:VITE_COGNITO_REGION = "ap-south-1"

npm run build
```

Output is in `dist/`. Do **not** use a localhost URL for `VITE_API_URL` in production build.

### 5.2 Deploy to S3 + CloudFront

Terraform creates:

- **Staff app:** S3 bucket `aws_s3_bucket.main`, CloudFront distribution `aws_cloudfront_distribution.staff_app`.
- **Patient portal:** S3 bucket `aws_s3_bucket.corpus`, CloudFront `aws_cloudfront_distribution.patient_portal`.

**Upload staff app (doctor-dashboard):**

```powershell
# After npm run build in doctor-dashboard
aws s3 sync dist/ s3://YOUR_STAFF_BUCKET_NAME/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_CF_DIST_ID --paths "/*"
```

Get bucket and distribution IDs from Terraform outputs (e.g. `terraform output`):

- Staff bucket: `terraform output -raw s3_bucket_name`
- Staff CloudFront ID: `terraform output -raw staff_app_cf_id`
- API base URL for build: `terraform output -raw api_gateway_url`

For **SPA routing**, Terraform configures CloudFront **custom error responses** (403/404 → 200, `/index.html`) so client-side routes (e.g. `/patients`, `/ai`) work when the user refreshes or opens a deep link.

### 5.3 Single Source for URLs

Keep one place for the production API URL (and optional WebSocket URL):

- **Option A:** `config/gateway-config.json` (or similar) with `apiBaseUrl`, and a small script or CI step that sets `VITE_API_URL` from it before `npm run build`.
- **Option B:** CI/CD (e.g. GitHub Actions) with secrets/vars for `VITE_API_URL` and Cognito, and build step that exports them before build.

Then frontend build and Terraform (e.g. docs or outputs) stay in sync.

---

## 6. Backend (Lambda) Deploy

Terraform packages the Lambda from `infrastructure/modules/lambda`: `source_dir = "${path.root}/../src"`. So:

- Code changes in `src/` require a **new zip** and Lambda update. Run from repo root:
  - `cd infrastructure && terraform apply` (recreates the zip and updates the function).
- Or use CI to build the zip, upload to S3, and run Terraform or `aws lambda update-function-code`.

Lambda env (RDS, Bedrock, S3, Cognito, etc.) is set in `infrastructure/main.tf`; no `.env` in production.

---

## 7. Order of Operations for First Production Deploy

1. **Terraform** — Apply with desired vars (`api_require_cognito`, `enable_lambda_vpc`, etc.). Apply the **health** fix (§4.1) so GET /health goes to CDSS Lambda.
2. **Secrets** — Set RDS and Bedrock secret values in AWS Secrets Manager (keys created by Terraform).
3. **Database** — Start bastion tunnel (or use runner with access); run migrations; optionally seed.
4. **Verify API** — `curl https://YOUR_API_URL/health` → expect `database` in JSON. `curl https://YOUR_API_URL/dashboard` (and if Cognito: add `Authorization: Bearer <token>`).
5. **Frontend** — Build with production `VITE_API_URL`; upload to S3; invalidate CloudFront; configure SPA fallback if needed.
6. **Smoke test** — Open CloudFront URL; check ApiHealthBanner (if health returns `database`); log in if Cognito; open Dashboard and Patients.

---

## 8. References

- **Implementation status and alignment:** [IMPLEMENTATION_STATUS_AND_COMPLETION.md](IMPLEMENTATION_STATUS_AND_COMPLETION.md)
- **Production readiness and deployment:** [PRODUCTION_READINESS_AND_DEPLOYMENT.md](PRODUCTION_READINESS_AND_DEPLOYMENT.md)
- **Pre-build checklist (keys, regions, secrets):** [PRE_BUILD_CHECKLIST.md](PRE_BUILD_CHECKLIST.md)
- **Frontend API and env:** [FRONTEND_API_AND_ENV.md](FRONTEND_API_AND_ENV.md)
- **After Terraform (tunnel, migrations):** [RUN_AFTER_TERRAFORM.md](RUN_AFTER_TERRAFORM.md)
- **API contract:** `docs/swagger.yaml`; Swagger UI at GET /api/docs (local; production per §4.2)

---

*Update this guide when you add new env vars, change API Gateway routes, or add deployment automation.*

---

## 9. Docker Deployment

For local production-like deployment, use Docker Compose:

```powershell
# Build and run all services
docker-compose up --build -d

# Access:
# Frontend: http://localhost
# Backend API: http://localhost:8080
# PostgreSQL: localhost:5432
```

**Services:**
- `postgres` (PostgreSQL 15) — port 5432, seeded with `backend/database/seed_data.sql`
- `backend` (Python API) — port 8080, connects to postgres
- `frontend` (Nginx + React) — port 80, proxies API calls to backend

**Environment variables for backend:**
- `DATABASE_URL` — PostgreSQL connection string (set automatically in docker-compose)
- `BEDROCK_CONFIG_SECRET_NAME` — AWS Secrets Manager key for Bedrock config (optional for local)
- `AWS_REGION` — AWS region (default: ap-south-1)

---

## 10. CI/CD Pipeline

GitHub Actions workflow at `.github/workflows/ci.yml`:

1. **backend-test** — Python syntax/import check + local handler tests
2. **frontend-build** — Node.js build with `VITE_USE_MOCK=false`
3. **docker-build** — Build and verify Docker images (main/choros branch only)

---

## 11. AI Agent Endpoints

| Endpoint | Agent | Purpose |
|----------|-------|---------|
| `POST /agent` | Supervisor | Intent-based routing to specialized agents |
| `POST /api/ai/summarize` | AI Summary | Clinical text/conversation summarization |
| `POST /api/ai/entities` | Entity Extraction | Medical entity extraction |
| `POST /api/ai/surgery-support` | Surgery Planning | Pre-op/post-op checklists and guidance |
| `POST /api/ai/translate` | Translation | Multilingual clinical translation |
| `POST /api/ai/prescription` | Prescription | AI-suggested prescriptions (doctor approval required) |
| `POST /api/ai/adherence` | Medication Adherence | Adherence analysis and risk scoring |
| `POST /api/ai/engagement` | Patient Engagement | Engagement scoring and alerts |
| `POST /api/ai/resources` | Patient Resources | Health education guides for diagnoses |

---

## 12. Database Indexes

Migration `005_performance_indexes.sql` adds indexes on:
- `visits(patient_id, doctor_id, visit_date)`
- `surgeries(patient_id, surgeon_id, scheduled_date, status)`
- `schedule_slots(ot_id, slot_date)`
- `medications(patient_id)`
- `reminders(patient_id, scheduled_at, sent_at)`
- `audit_log(user_id, timestamp, resource)`
- `patients(name)`

Run: `psql -f src/cdss/db/migrations/005_performance_indexes.sql`
