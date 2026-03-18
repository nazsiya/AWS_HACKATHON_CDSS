## CDSS Deployment & Database Connectivity – Technical Assessment and RCA

### Purpose

This document summarizes the current state of the CDSS application with a focus on deployment and database connectivity. It documents **what is working**, **what is not working**, **what needs improvement**, and provides a **root cause analysis (RCA)** of the database connection issues, along with a recovery plan.

---

## 1. What Is Working

### 1.1 Backend Architecture & DB Abstraction

- **Centralized DB session management**
  - SQLAlchemy-based engine and session management is implemented in `src/cdss/db/session.py`.
  - The module:
    - Reads `DATABASE_URL` when present.
    - Otherwise builds a secure IAM-based URL from `RDS_CONFIG_SECRET_NAME` and `AWS_REGION` using AWS Secrets Manager and `boto3.client("rds").generate_db_auth_token`.
    - Supports local tunnel overrides via `TUNNEL_LOCAL_PORT` for SSM/SSH-based access to Aurora.
    - Uses `pool_pre_ping`, conservative pool sizes, and `connect_timeout` with optional SQL echo (`SQL_ECHO`) for safer operation.
  - `get_session()` provides a context-managed session with automatic commit/rollback and cleanup, aligning with project standards.

- **Gateway tools Lambda DB behavior**
  - `infrastructure/gateway_tools_src/lambda_handler.py` reuses the same configuration pattern:
    - Prefers `RDS_CONFIG_SECRET_NAME` + `AWS_REGION` for IAM-based Aurora connectivity.
    - Falls back to `DATABASE_URL` if secrets are not present.
    - When no DB configuration is available, tools degrade gracefully to synthetic data with explicit safety disclaimers, instead of failing hard.

- **Local Docker-based development DB**
  - `docker-compose.yml` defines a `postgres` service using:
    - `POSTGRES_DB=cdss`
    - `POSTGRES_USER=cdss_admin`
    - `POSTGRES_PASSWORD=cdss_secure_password`
  - The `backend` service:
    - Uses `DATABASE_URL=postgresql://cdss_admin:cdss_secure_password@postgres:5432/cdss`.
    - Correctly references the DB via the Docker service name `postgres` (no localhost/networking mistakes inside the compose network).
  - `scripts/local_db_setup.py` provides a robust local bootstrap:
    - Starts a Postgres 15 container (outside of compose if needed).
    - Applies `backend/database/refined_schema.sql` and `backend/database/seed_data.sql`.

### 1.2 Frontend and Infrastructure Stitching

- **Frontend build and deployment**
  - `Dockerfile.frontend` builds the doctor dashboard using Vite and serves it via Nginx.
  - Build-time configuration is driven by:
    - `VITE_API_URL` (points to API Gateway URL).
    - `VITE_USE_MOCK` (controls mock vs real backend data).
    - Auth-related variables (Cognito) where applicable.

- **Infrastructure as Code**
  - Terraform (`infrastructure/*.tf`) defines the primary production stack:
    - VPC, subnets, and security groups.
    - Aurora (RDS) cluster.
    - Lambda functions and API Gateway configuration.
    - IAM roles and policies that support IAM-based DB access (no hardcoded credentials).
  - CI (`.github/workflows/ci.yml`) validates:
    - Backend Python (lint/tests).
    - Frontend build.
    - Docker images and basic container-level behavior.

- **Security posture**
  - The repository does not contain real `.env` files; only `.env.example` templates are checked in.
  - No AWS access keys or secret keys are committed; only SDK examples mention `aws_access_key_id` and `secret_access_key`.
  - Secrets are expected to be provided via AWS Secrets Manager and IAM roles, matching the project’s security guidance.

---

## 2. What Is Not Working

### 2.1 Configuration Drift Between CDK Stack and Application Code

- The **CDK-based stack** in `infra/lib/cdss-stack.ts` configures the dashboard REST Lambda with:
  - `DB_CLUSTER_ARN`
  - `DB_SECRET_ARN`
- The **dashboard Lambda code** in `backend/api/rest/database_crud.py` expects:
  - `RDS_CONFIG_SECRET_NAME` and `AWS_REGION` (for IAM/Secrets Manager), or
  - Direct database parameters via `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`.
- There is no direct consumption of `DB_SECRET_ARN` in this module.
  - Result: When the CDK stack is deployed without an adapter or additional env wiring, the Lambda does not know which secret to read and will fail to establish a DB connection.

### 2.2 Dual DB Configuration Paradigms

- The codebase currently supports **two separate configuration patterns**:
  - **Pattern A (canonical SQLAlchemy path)**:
    - `DATABASE_URL` (explicit URL).
    - `RDS_CONFIG_SECRET_NAME` + `AWS_REGION` (IAM-based URL).
  - **Pattern B (REST dashboard psycopg2 path)**:
    - `RDS_CONFIG_SECRET_NAME` + `AWS_REGION`, or
    - Individual `DB_*` environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`).
- This split increases operational risk:
  - Different services may be using different environment variables for the “same” DB.
  - Some Lambdas may be correctly configured for Pattern A, while Pattern B Lambdas are left partially configured or broken.

### 2.3 Environment Name and User Mismatch (Local vs Aurora)

- **Local Docker Postgres** (compose):
  - Database name: `cdss`
  - Username: `cdss_admin`
- **Aurora (production)**:
  - Database name: `cdssdb`
  - Username: `cdssadmin`
- These differences are intentional but fragile:
  - Using an Aurora-style `DATABASE_URL` (`cdssdb` / `cdssadmin`) against the compose DB will fail with authentication errors.
  - Using compose-style credentials against Aurora will also fail.
  - This can easily be misinterpreted as a generic “connectivity issue” rather than a credential/schema mismatch.

### 2.4 Health Endpoint and DB Status Alignment

- Historical behavior (documented elsewhere) shows:
  - Health checks have not always reflected **database connectivity**, especially when separate health Lambdas were used.
  - The current design routes `/health` via the router Lambda, but this depends on the correct Terraform version being deployed.
- If infrastructure is out of sync with the latest design:
  - The frontend health banner may show “healthy” while DB connectivity is degraded or broken.

---

## 3. What Needs Improvement

### 3.1 Single Source of Truth for DB Configuration

- The project should standardize around a **single canonical DB configuration contract**:
  - **Cloud (Lambda/Aurora)**:
    - Prefer `RDS_CONFIG_SECRET_NAME` + `AWS_REGION`, with the secret containing host, port, database, and username.
    - Use IAM tokens (`generate_db_auth_token`) for passwords.
  - **Local (developer machines and CI)**:
    - Prefer `DATABASE_URL` profiles for:
      - Local Docker Postgres.
      - Aurora via SSM/SSH tunnel.
- The `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS` pattern should:
  - Either be wrapped via a helper that produces a `DATABASE_URL`, or
  - Be explicitly deprecated in favor of the existing Secrets Manager contract.

### 3.2 Infra–Code Contract Alignment

- The CDK stack currently exports `DB_SECRET_ARN`, but application code is designed for `RDS_CONFIG_SECRET_NAME`.
- Terraform uses `RDS_CONFIG_SECRET_NAME` consistently.
- To reduce surprises:
  - Choose **one** environment variable convention for DB secrets (recommended: `RDS_CONFIG_SECRET_NAME`).
  - Ensure all stacks (Terraform, CDK, manual deployments) expose this variable consistently to every DB-using Lambda.

### 3.3 Observability and Automated DB Health Checks

- While DB failures will eventually surface in logs, they are not always surfaced via:
  - A standardized health endpoint, or
  - CI/CD gating checks.
- A more robust approach would:
  - Provide a canonical health route (e.g. `/health` or `/health/db`) that internally:
    - Acquires a SQLAlchemy session via `get_session()`.
    - Executes a `SELECT 1` against the configured DB.
  - Wire `scripts/check_connectivity.py` or an equivalent health script into:
    - CI pipelines (pre-deploy).
    - Post-deploy checks and dashboards.

### 3.4 Version Drift Management

- DB-related dependencies are present both:
  - In Lambda layers (`infrastructure/layer/python/**`), and
  - In local Docker images (via `pyproject.toml` and `requirements.txt`).
- If application dependencies are updated without rebuilding Lambda layers:
  - Behavior may diverge between local dev and the deployed Lambdas.
  - This can complicate debugging, especially around DB connection handling.

---

## 4. RCA – What Went Wrong with Database Connection

### 4.1 Symptoms

- Lambdas (particularly the **CDK-deployed dashboard Lambda**) report:
  - Connection failures when attempting to reach Aurora.
  - Or fallback behavior (synthetic data) instead of querying the real DB.
- Locally, developers may observe:
  - Authentication errors when switching between local Docker Postgres and Aurora via tunnels.
  - Intermittent “connection refused” or timeout errors when tunnels are not correctly configured.

### 4.2 Contributing Factors

1. **Misaligned environment variables in the CDK stack**
   - The CDK stack sets `DB_SECRET_ARN`, but `backend/api/rest/database_crud.py` expects `RDS_CONFIG_SECRET_NAME` (or `DB_*` env vars).
   - No adapter exists in the code to translate `DB_SECRET_ARN` into the expected configuration contract.
   - As a result, `_get_db_config()` either:
     - Fails to retrieve any secret, or
     - Falls back to default `DB_HOST`/`DB_PORT` values that are incorrect for the deployed Aurora cluster.

2. **Dual configuration paradigms without clear guidance**
   - Some parts of the system rely solely on `DATABASE_URL` and `RDS_CONFIG_SECRET_NAME`.
   - Other parts expect `DB_*` variables or a different secret naming scheme.
   - This causes “partial configuration,” where one service is correctly wired but another is not, even though both are talking to the same DB.

3. **Local vs Aurora naming mismatch**
   - Developers sometimes reuse a `DATABASE_URL` intended for one environment (e.g., Aurora) against another (e.g., the compose Postgres container).
   - Due to differences in database name and user, this surfaces as “connectivity issues,” masking the underlying credential mismatch.

4. **Inconsistent health and monitoring**
   - A failing DB connection does not always cause an immediate, visible failure at the platform level:
     - Some Lambdas may revert to synthetic data.
     - Health endpoints may not include a DB check.
   - This delays detection of misconfiguration and complicates RCA.

### 4.3 Root Cause (Primary)

The **primary root cause** of the observed database connection issues is **configuration mismatch between the infrastructure and the application code**, specifically:

- The CDK stack’s use of `DB_SECRET_ARN` and related fields without providing the `RDS_CONFIG_SECRET_NAME` contract that `backend/api/rest/database_crud.py` and `src/cdss/config/secrets.py` expect.
- This leads to the dashboard Lambda attempting to operate without a valid DB configuration, resulting in connection failures even though Aurora itself is correctly provisioned and reachable.

### 4.4 Secondary Causes

- Lack of a single, enforced DB configuration pattern across all services.
- Environment-specific differences (local vs Aurora DB names and users) that are not encapsulated behind clear profiles.
- Limited automated health checks that explicitly validate DB connectivity during CI and post-deploy stages.

---

## 5. Recovery Roadmap (Top 3 Immediate Fixes)

### 5.1 Standardize and Enforce the DB Configuration Contract

- **Cloud (production/staging):**
  - Mandate `RDS_CONFIG_SECRET_NAME` (+ `AWS_REGION`) as the canonical way to configure DB access for all Lambdas (Terraform and CDK).
  - Ensure the referenced secret contains `host`, `port`, `database`, `username`, and `region` fields compatible with `cdss.config.secrets.get_rds_config`.
- **Local (developer/CI):**
  - Define two explicit `DATABASE_URL` profiles:
    - `LOCAL_DOCKER_DB` – points to the compose Postgres service (`cdss` / `cdss_admin`).
    - `AURORA_TUNNEL_DB` – points to Aurora via SSM/SSH tunnel (`cdssdb` / `cdssadmin` on `localhost:5433`).
  - Provide helper scripts or `.env` templates that make it trivial to switch between the two.

### 5.2 Align Infrastructure with Application Expectations

- Update the **CDK stack** to respect the application’s DB contract:
  - Option A: Set `RDS_CONFIG_SECRET_NAME` in the Lambda environment to the correct secret name and remove reliance on `DB_SECRET_ARN` within the app.
  - Option B: Add a small adapter that:
    - Reads `DB_SECRET_ARN`.
    - Fetches the corresponding secret JSON.
    - Either populates `RDS_CONFIG_SECRET_NAME` or directly constructs the required config for `database_crud.py`.
- Ensure that **Terraform** and **CDK** stacks both expose the same env variables (`RDS_CONFIG_SECRET_NAME`, `AWS_REGION`) to any function that touches the DB.

### 5.3 Add a Mandatory DB Connectivity Health and CI Check

- Extend or standardize a health endpoint (e.g. `/health` or `/health/db`) that:
  - Uses `src/cdss/db/session.get_session()` (or equivalent) to perform a `SELECT 1`.
  - Returns a clear status field for DB connectivity (e.g. `database: "connected" | "unavailable"`).
- Integrate `scripts/check_connectivity.py` (or a similar lightweight script) into:
  - CI pipelines, executed against staging environments before promoting builds.
  - Post-deploy automation and monitoring dashboards.
- In non-development environments, treat the absence of both `DATABASE_URL` and `RDS_CONFIG_SECRET_NAME` as a **hard failure**:
  - Fail fast during Lambda cold start or container startup.
  - Avoid silently falling back to synthetic data in production.

---

By implementing these steps, the CDSS project will have a consistent, secure, and observable database connectivity story across local, staging, and production environments, significantly reducing the risk of deployment-time surprises and simplifying future RCAs.

