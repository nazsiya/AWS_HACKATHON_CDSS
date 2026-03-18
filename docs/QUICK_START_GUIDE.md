# CDSS Quick Start Guide

This guide explains how to start your development environment and connect to the Aurora database.

## 1. Prerequisites
- **AWS Credentials:** Ensure your AWS CLI is configured (`aws configure`).
- **Python Env:** Activate the virtual environment (`.venv\scripts\activate`).
- **Frontend env:** For real data, set `frontend/apps/doctor-dashboard/.env.local`:
  - `VITE_API_URL=http://localhost:8080`
  - `VITE_USE_MOCK=false`
  (See [CONNECTION_TROUBLESHOOTING.md](CONNECTION_TROUBLESHOOTING.md) if you see connection errors.)

## 2. Startup Procedure

### Step 1: Start the SSH Tunnel (Terminal 1)
The database is in a private network. You **must** keep this tunnel running to connect.
```powershell
.\scripts\start_ssh_tunnel.ps1
```

### Step 2: Migrations and seed (Terminal 2 – one time or after reset)
With the tunnel running and `DATABASE_URL=postgresql://...@localhost:5433/cdssdb` in repo root `.env`:
```powershell
.\scripts\run_migrations_and_seed.ps1
```
To force re-seed: `python -m cdss.db.seed --force` (or use the script then seed with `--force`).

### Step 3: Start the backend API (Terminal 2)
The frontend needs this running to show real data (otherwise you get "Backend is not connected to the database").
```powershell
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```
You should see `Data source: database` and `http://localhost:8080`.

### Step 4: Start the Frontend (Terminal 3)
```powershell
cd frontend/apps/doctor-dashboard
npm run dev
```
Open the URL shown (usually `http://localhost:5173` or `5174`).

## 3. Test Credentials
Use your Cognito or local mock credentials to log in to the dashboard (do not commit real passwords; contact team for demo access if needed).

## 4. Clinical Safety Verification (Phase 5–6)
Before using in a clinical setting, verify the following safety mechanisms:
```powershell
# Test vital alerts and drug interactions
python scripts/test_phase5_alerts.py

# Run safety-critical path tests & RBAC boundaries
python scripts/test_critical_paths.py
python scripts/test_rbac_boundaries.py
```

## 5. Documentation & Handover
- **Central Reference**: See [PROJECT_REFERENCE.md](file:///d:/AI_Hackathon_CDSS/docs/PROJECT_REFERENCE.md) for ARNs and endpoints.
- **Runbooks**: See [RUNBOOKS.md](file:///d:/AI_Hackathon_CDSS/docs/RUNBOOKS.md) for deployment and incident recovery.
- **Onboarding**: New developers should follow [ONBOARDING.md](file:///d:/AI_Hackathon_CDSS/docs/ONBOARDING.md).

---
*For issues, see [DEBUGGING_REPORT_2026_03_08.md](file:///d:/AI_Hackathon_CDSS/docs/DEBUGGING_REPORT_2026_03_08.md).*
