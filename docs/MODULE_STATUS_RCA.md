## CDSS Module Status and RCA

### Purpose

This document provides a module-level view of the Clinical Decision Support System (CDSS), focusing on:

- **What is working** (modules that are implemented and integrated as designed).
- **What is not working or fragile** (modules with known alignment or deployment issues).
- **What needs improvement** (design, security, or operational gaps).
- **Root cause analysis (RCA)** for the most critical module-level failures.

It is intended for solutions architects, DevOps engineers, and lead developers responsible for maintaining and extending the system.

---

## 1. Module Inventory

At a high level, the CDSS consists of the following module groups:

- **Backend API (Router Lambda)** – Core clinical and AI APIs under `src/cdss/**`.
- **Gateway Tools Lambda** – Bedrock AgentCore integration under `infrastructure/gateway_tools_src/**`.
- **REST Dashboard Lambda (CDK path)** – Auxiliary REST API under `backend/api/rest/**`, wired by CDK.
- **Agents and Shared Libraries** – AI/agent modules under `backend/agents/**` and `src/cdss/**`.
- **Frontend Dashboards** – Doctor, Nurse, and Patient dashboards under `frontend/apps/**`.
- **Infrastructure as Code** – Terraform under `infrastructure/**` and CDK under `infra/**`.
- **Operational Scripts & Tooling** – Scripts under `scripts/**` for connectivity, migrations, seeding, and checks.

The sections below classify these modules by status.

---

## 2. What Is Working

### 2.1 Backend API (Router Lambda)

- **Module**: `src/cdss/api/handlers/router.py` and related `src/cdss/api/**` handlers.
- **Status**: **Working / production path**
  - Implements the primary HTTP interface for:
    - Clinical endpoints (patients, surgeries, schedule, appointments, tasks).
    - AI endpoints (e.g., prescription, adherence, engagement, resources).
  - Integrated with:
    - API Gateway (Terraform stack).
    - SQLAlchemy-based DB layer (`src/cdss/db/session.py`).
    - Bedrock agents via shared utilities in `backend/agents/shared/**`.
  - Local and production behavior is validated via:
    - `scripts/check_connectivity.py`
    - `docs/PRODUCTION_READINESS_AND_DEPLOYMENT.md`

### 2.2 Database Session & Models

- **Module**: `src/cdss/db/session.py` and `src/cdss/db/models.py` (and related models).
- **Status**: **Working / stable**
  - Provides centralized engine and session lifecycle management with:
    - Support for `DATABASE_URL` and IAM-based `RDS_CONFIG_SECRET_NAME`.
    - Pooling and connection timeouts suitable for Lambda workloads.
    - Safe commit/rollback semantics.
  - Actively used by:
    - The router Lambda.
    - Connectivity scripts (e.g., `scripts/check_connectivity.py`, `scripts/check_aurora_db.py`).

### 2.3 Gateway Tools Lambda (Bedrock Integration)

- **Module**: `infrastructure/gateway_tools_src/lambda_handler.py` and associated tool implementations.
- **Status**: **Working with graceful degradation**
  - Implements multi-agent tools for:
    - Patients, surgeries, scheduling, resources, reminders/adherence.
  - DB behavior:
    - Uses IAM/Secrets Manager via `RDS_CONFIG_SECRET_NAME` when present.
    - Falls back to `DATABASE_URL` if set.
    - Otherwise operates in synthetic mode with explicit safety disclaimers.
  - This design prevents Lambda hard failures when DB is temporarily misconfigured.

### 2.4 Frontend Dashboards (Core Flows)

- **Modules**:
  - Doctor dashboard: `frontend/apps/doctor-dashboard/**`.
  - Nurse dashboard: `frontend/apps/nurse-dashboard/**`.
  - Patient dashboard: `frontend/apps/patient-dashboard/**`.
- **Status**: **Working for primary flows**
  - Doctor dashboard:
    - Integrates with the main API via `VITE_API_URL`.
    - Uses real schedule/appointments/tasks APIs when `VITE_USE_MOCK=false`.
  - Nurse and Patient dashboards:
    - Share common auth/context modules.
    - Use the same API base pattern and feature flags.
  - Build and deployment via `Dockerfile.frontend` and CI workflows is in place.

### 2.5 Terraform Infrastructure

- **Module**: `infrastructure/*.tf`.
- **Status**: **Working / primary IaC**
  - Provisions:
    - VPC and networking.
    - Aurora PostgreSQL cluster (see `docs/PROJECT_REFERENCE.md`).
    - Router Lambda, Gateway Tools Lambda, and supporting roles.
    - API Gateway routes for `/health`, `/api/**`, and related paths.
  - Aligns with application expectations around:
    - `RDS_CONFIG_SECRET_NAME` and `AWS_REGION`.
    - Health endpoints and CORS.

---

## 3. What Is Not Working or Fragile

### 3.1 REST Dashboard Lambda (CDK Path)

- **Module**:
  - `backend/api/rest/database_crud.py`
  - `infra/lib/cdss-stack.ts`
- **Status**: **Not fully aligned / at risk**
  - CDK stack configures the dashboard Lambda with:
    - `DB_CLUSTER_ARN` and `DB_SECRET_ARN`.
  - Application code expects:
    - `RDS_CONFIG_SECRET_NAME` and `AWS_REGION`, or
    - `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS`.
  - There is no direct usage of `DB_SECRET_ARN` in `database_crud.py`.
  - Consequence:
    - The Lambda may start without a valid DB configuration and fail to connect to Aurora.
    - This module is best treated as **experimental/PoC** until configuration is brought in line with the rest of the system.

### 3.2 Dual DB Configuration Patterns Across Modules

- **Modules**:
  - `src/cdss/db/session.py`
  - `infrastructure/gateway_tools_src/lambda_handler.py`
  - `backend/api/rest/database_crud.py`
  - Various scripts under `scripts/**`
- **Status**: **Operationally fragile**
  - Two separate patterns are in use:
    - **Pattern A**: `DATABASE_URL` and `RDS_CONFIG_SECRET_NAME` (canonical for router/gateway tools).
    - **Pattern B**: `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS` (used by `database_crud.py`).
  - This introduces:
    - Inconsistent configuration between services.
    - Higher risk that one module is correctly wired while another is not.

### 3.3 Local vs Aurora DB Naming/Users

- **Modules**:
  - `docker-compose.yml`
  - `scripts/local_db_setup.py`
  - Scripts that construct `DATABASE_URL` for Aurora (e.g., connectivity and migration scripts).
- **Status**: **Confusing for new operators**
  - Local compose DB:
    - `POSTGRES_DB=cdss`
    - `POSTGRES_USER=cdss_admin`
  - Aurora (per `docs/PROJECT_REFERENCE.md`):
    - `Database Name = cdssdb`
    - `Master Username = cdssadmin`
  - Mixing credentials between environments leads to authentication failures that look like generic connectivity issues.

### 3.4 Health Checks and Monitoring Consistency

- **Modules**:
  - Router health endpoint (`/health`).
  - Frontend health banner components.
  - Any legacy or alternative health Lambdas mentioned in docs.
- **Status**: **Historically misaligned**
  - Earlier versions used a separate health Lambda that did not check DB status, while the frontend expected DB-aware health.
  - While current design routes `/health` through the router Lambda, there is a risk that:
    - Some environments are still using older health configurations.
    - DB connectivity issues are not surfaced clearly to operators or the UI.

---

## 4. What Needs Improvement

### 4.1 Module-Level Configuration Contracts

- Define and document a **single, canonical DB configuration contract** shared by:
  - Router Lambda.
  - Gateway Tools Lambda.
  - Dashboard/REST Lambdas (CDK or Terraform).
  - Operational scripts under `scripts/**`.
- Recommended contract:
  - Cloud: `RDS_CONFIG_SECRET_NAME` and `AWS_REGION` (with IAM-based auth).
  - Local: `DATABASE_URL` with clear, environment-specific profiles.
- Deprecate or encapsulate the `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS` pattern where possible.

### 4.2 CDK Stack Alignment

- Bring CDK resources under `infra/**` into alignment with:
  - Secret naming (`cdss-dev/rds-config` as defined in `docs/PROJECT_REFERENCE.md`).
  - Env var names (`RDS_CONFIG_SECRET_NAME`, not just `DB_SECRET_ARN`).
- Ensure any Lambdas created by CDK that use the DB:
  - Reuse the same Python helpers (`src/cdss/config/secrets.py`, `src/cdss/db/session.py`) where feasible.
  - Do not introduce new, one-off DB connection patterns.

### 4.3 Health & Diagnostics Modules

- Standardize module-level health:
  - Backends should expose a consistent `/health` contract including DB status.
  - Frontends should consume that contract and display clear, actionable states.
- Scripts like `scripts/check_connectivity.py` should be:
  - Treated as first-class diagnostics.
  - Integrated into CI and post-deploy workflows to validate module connectivity.

### 4.4 Documentation and Onboarding

- Expand documentation in `docs/**` to include:
  - A short “module map” highlighting which modules are production-critical vs PoC.
  - Examples of correct `DATABASE_URL` values for:
    - Local compose.
    - Aurora via tunnel.
    - Aurora via IAM (no tunnel).
  - Clear instructions for when to use each dashboard (doctor/nurse/patient) and how they relate to backends and health endpoints.

---

## 5. Module-Level RCA – What Went Wrong

### 5.1 REST Dashboard Lambda (CDK Path)

**Modules**: `backend/api/rest/database_crud.py`, `infra/lib/cdss-stack.ts`  
**Status**: Misconfigured DB connectivity in some deployments.

#### 5.1.1 Observed Behavior

- Dashboard REST Lambda deployed via CDK:
  - Starts successfully but fails when attempting DB operations, or
  - Operates without a real DB connection in environments where it is expected to talk to Aurora.

#### 5.1.2 Technical Cause

- The CDK stack sets:
  - `DB_CLUSTER_ARN`
  - `DB_SECRET_ARN`
- The Python module `database_crud.py` expects:
  - `RDS_CONFIG_SECRET_NAME` and `AWS_REGION` for `cdss.config.secrets.get_rds_config`, or
  - Fully specified `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASS`.
- There is no bridging logic between `DB_SECRET_ARN` and `RDS_CONFIG_SECRET_NAME` in this code path.
- As a result:
  - `_get_db_config()` either receives no configuration or falls back to defaults that do not point at the Aurora cluster.

#### 5.1.3 Underlying Root Cause

- **Configuration contract mismatch** between:
  - The **IaC module** (CDK stack) and
  - The **application module** (`database_crud.py` and `cdss.config.secrets`).
- The core system standardized on `RDS_CONFIG_SECRET_NAME`, but the CDK PoC introduced a parallel pattern using `DB_SECRET_ARN` without completing the integration.

#### 5.1.4 Impact

- REST dashboard endpoints created via CDK:
  - Cannot reliably query Aurora.
  - May give the impression of a broken or “down” system even when the main router Lambda and DB are healthy.

### 5.2 Cross-Module DB Configuration Drift

**Modules**: `src/cdss/db/session.py`, `infrastructure/gateway_tools_src/lambda_handler.py`, `backend/api/rest/database_crud.py`, selected `scripts/**`.

#### 5.2.1 Observed Behavior

- Some modules connect successfully using:
  - `DATABASE_URL` (local).
  - `RDS_CONFIG_SECRET_NAME` (cloud).
- Others:
  - Rely on plain `DB_*` env vars.
  - Or assume different secret naming conventions.
- When environment variables are set for one pattern but not the other:
  - Certain modules work correctly.
  - Other modules fail or fall back to mocks/synthetic data.

#### 5.2.2 Technical Cause

- Lack of a **single, enforced, shared configuration abstraction** for DB connectivity across modules.
- Each module (or IaC stack) made locally reasonable choices, but:
  - These choices were not consolidated into a single project-wide contract.

#### 5.2.3 Underlying Root Cause

- **Incremental evolution** of the codebase:
  - Initial router and scripts standardized on `DATABASE_URL` and `RDS_CONFIG_SECRET_NAME`.
  - Subsequent modules (e.g., CDK-based REST Lambda) introduced new patterns without fully adopting the shared helpers.

#### 5.2.4 Impact

- Increased operational complexity when:
  - Onboarding new environments.
  - Debugging connectivity issues.
  - Switching between local compose, tunnels, and IAM-based Aurora.

---

## 6. Recovery Recommendations (Module-Level)

1. **Promote Router Lambda + Gateway Tools as the canonical backend path**
   - Treat the Terraform-based stack and SQLAlchemy session module as the source of truth.
   - Only bring the CDK-based REST Lambda into production once its configuration is aligned.

2. **Refactor CDK dashboard Lambda to use shared helpers**
   - Replace direct psycopg2 config in `database_crud.py` with a wrapper that:
     - Uses `cdss.config.secrets.get_rds_config`.
     - Optionally constructs a SQLAlchemy engine via `src/cdss/db/session.py` for consistency.

3. **Introduce a shared “DB config” utility module**
   - Expose a single function (e.g., `get_db_config()` or `get_db_url()`) in `src/cdss/config/` that:
     - Implements the full configuration logic.
     - Is reused by:
       - Router Lambda.
       - Gateway Tools Lambda.
       - REST dashboard Lambdas.
       - Operational scripts (where appropriate).

These changes will reduce divergence between modules, simplify future RCAs, and make the system’s behavior more predictable across environments.

