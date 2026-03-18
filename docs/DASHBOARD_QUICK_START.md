# Dashboard Quick Start — Get Fully Functional

You’ve completed the development phases and have [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md). Use this guide to get the **doctor dashboard** fully functional, then optionally wire auth and Phase 4.

---

## 1. One-time setup (from PROJECT_REFERENCE.md)

Values below come from **docs/PROJECT_REFERENCE.md**. Keep them in sync when config changes.

### 1.1 Frontend env (doctor-dashboard)

**Location:** `frontend/apps/doctor-dashboard/`

Create or edit **`.env`** or **`.env.local`** (Vite reads from this app folder, not repo root):

**Option A — Local API (recommended for “fully functional” first):**

```env
VITE_API_URL=http://localhost:8080
VITE_USE_MOCK=false
```

**Option B — Deployed API (AWS):**

```env
VITE_API_URL=https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev
VITE_USE_MOCK=false
```

If the deployed API requires an API key (e.g. 403):

```env
VITE_API_KEY=your-api-key-here
```

**Cognito (optional; for real login):** From PROJECT_REFERENCE.md:

```env
VITE_COGNITO_USER_POOL_ID=ap-south-1_0eRSiDzbY
VITE_COGNITO_CLIENT_ID=15hk1uremldsor79jkc7cr866v
VITE_COGNITO_REGION=ap-south-1
```

After any change: **restart the dev server** and hard-refresh the browser (Ctrl+Shift+R).

### 1.2 Backend env (for local API)

**Location:** repo root **`.env`**

- **Without real DB (mock data):** You can leave `DATABASE_URL` unset. The local API will use in-memory mock data and `/health` will show `"database": "unavailable"`; dashboard and patients/surgeries will still load from mock.
- **With real DB (Aurora):** Start the tunnel (e.g. `.\scripts\start_ssm_tunnel.ps1`), then set:
  ```env
  DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb
  ```
  Port **5433** = local tunnel port (see PROJECT_REFERENCE.md).

---

## 2. Get the dashboard working (step-by-step)

### Step 1: Start the backend (local API)

From **repo root**:

```powershell
$env:PYTHONPATH='src'; python scripts/run_api_local.py
```

Or if 8080 is in use:

```powershell
$env:PORT='8081'; $env:PYTHONPATH='src'; python scripts/run_api_local.py
```

Then use `VITE_API_URL=http://localhost:8081` in the frontend.

**Check:** Open `http://localhost:8080/health` (or 8081). You should see:

```json
{"service":"cdss","status":"ok","user_id":"anonymous"}
```

If you set `DATABASE_URL` and the DB is reachable, you should also see `"database":"connected"`.

### Step 2: Start the frontend

From **repo root**:

```powershell
cd frontend\apps\doctor-dashboard
npm install
npm run dev
```

Or from repo root with npm workspaces:

```powershell
cd frontend
npm run dev:dashboard
```

**Check:** Open `http://localhost:5173`. You should see the dashboard (with mock or real data depending on API + DB).

### Step 3: Verify connectivity

From repo root (with API already running):

```powershell
.\scripts\run_phase3_verify.ps1
```

Or:

```powershell
$env:BASE_URL='http://localhost:8080'; python scripts/verify_phase3_connectivity.py
```

This checks GET `/health` and GET `/api/v1/patients`. If either fails, fix the API URL or DB/tunnel before continuing.

### Step 4 (optional): Real data from Aurora

1. Start DB tunnel: `.\scripts\start_ssm_tunnel.ps1` (keep it open).
2. In repo root `.env`: `DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb`.
3. Apply migrations and seed (if not already):
   ```powershell
   python scripts/run_migrations.py
   python scripts/seed_db.py
   ```
4. Restart the local API. GET `/health` should show `"database":"connected"`.
5. Restart the frontend; dashboard and Patients/Surgeries should show DB data.

---

## 3. Troubleshooting “dashboard not fully functional”

| Symptom | Likely cause | What to do |
|--------|----------------|------------|
| “Cannot reach API at …” / Failed to fetch | Wrong `VITE_API_URL` or API not running | Set `VITE_API_URL=http://localhost:8080` (or your API port). Start backend with `python scripts/run_api_local.py`. Restart frontend and hard-refresh. |
| Empty patients / surgeries / dashboard KPIs | API using mock data or DB empty | With local API: set `DATABASE_URL` and start tunnel; run seed. Or call GET `/api/v1/patients` and GET `/dashboard` in browser/Postman to confirm responses. |
| Yellow banner: “Backend is not connected to the database” | DB not connected | Expected if you’re not using Aurora. For real data: start tunnel, set `DATABASE_URL`, restart API. Or dismiss banner and use mock data. |
| Login doesn’t work / redirects wrong | Cognito not configured or wrong IDs | Set `VITE_COGNITO_USER_POOL_ID` and `VITE_COGNITO_CLIENT_ID` (from PROJECT_REFERENCE.md) in `frontend/apps/doctor-dashboard/.env.local`. Ensure API Gateway authorizer uses the same Cognito pool. |
| CORS errors when calling deployed API from localhost | API Gateway CORS | For local dev, prefer `VITE_API_URL=http://localhost:8080` and run the API locally. If you must use deployed API from localhost, add your origin (e.g. `http://localhost:5173`) to the API Gateway CORS config. |
| 403 on API requests | Missing or wrong auth / API key | If using Cognito, ensure token is sent (login first). If Gateway requires `x-api-key`, set `VITE_API_KEY` in frontend env. |

---

## 4. Quick reference (from PROJECT_REFERENCE.md)

| Item | Value |
|------|--------|
| Local API | `http://localhost:8080` |
| Production API | `https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev` |
| WebSocket | `wss://jcw3vemil9.execute-api.ap-south-1.amazonaws.com/dev` |
| Cognito User Pool | `ap-south-1_0eRSiDzbY` |
| Cognito Staff Client | `15hk1uremldsor79jkc7cr866v` |
| DB (local tunnel port) | `5433` |

---

## 5. What to do after the dashboard is functional

From [DEVELOPMENT_COMPLETION_STEPS.md](DEVELOPMENT_COMPLETION_STEPS.md):

1. **Phase 4 (next):** Medical audit dashboard, RBAC enforcement, audit trails, data localization, encryption. Run Phase 4 AI check: `.\scripts\run_phase4_verify.ps1` or `BASE_URL=http://localhost:8080 python scripts/verify_phase4_ai.py`.
2. **Phase 5:** Notifications and alerts (drug interaction, emergency protocols, escalation).
3. **Phase 6:** Tests, performance, SLO, compliance.
4. **Phase 7:** Docs and runbooks (keep PROJECT_REFERENCE.md and api_reference.md in sync).

Keep [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) as the single source for IDs, ARNs, and endpoints.
