# CDSS Connection Troubleshooting

Use this when you see:
- **"Backend is not connected to the database"** (yellow banner)
- **"Cannot reach API"** or frontend not loading real data

---

## One command to fix both (recommended)

From **repo root** in PowerShell:

```powershell
.\scripts\run_dev_backend.ps1
```

This script:
1. Loads `.env` from the repo root (so `DATABASE_URL` is set).
2. If nothing is listening on port **5433**, opens a **new window** and runs the SSH tunnel there (leave that window open).
3. Waits for the tunnel, then starts the API in the **current** window on **http://localhost:8080**.

**Leave that terminal open.** Then in a **second terminal**:

```powershell
cd frontend\apps\doctor-dashboard
npm run dev
```

Open the URL Vite prints (e.g. http://localhost:5173) and hard-refresh (Ctrl+Shift+R). Both errors should be gone.

---

## 1. Check your current setup

### Frontend (`frontend/apps/doctor-dashboard/.env.local`)

For **local development** (backend on your machine):

```env
VITE_API_URL=http://localhost:8080
VITE_USE_MOCK=false
```

For **deployed API** (AWS API Gateway):

```env
VITE_API_URL=https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev
VITE_USE_MOCK=false
```

**Verify:**

```powershell
# PowerShell
Get-Content frontend\apps\doctor-dashboard\.env.local
```

File must be UTF-8 (no BOM). If you see spaces between every character, re-save as plain UTF-8.

---

## 2. Start the database tunnel (for AWS RDS/Aurora)

The database is in a private VPC. You must run the SSH tunnel and **leave that terminal open**.

```powershell
# Windows (PowerShell) – from repo root
.\scripts\start_ssh_tunnel.ps1
```

This forwards **localhost:5433** → Aurora:5432. Do not close this terminal.

---

## 3. Configure backend database connection

**Backend** uses the repo root `.env` (not inside `frontend/`).

Ensure:

```env
DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb
```

- Use **5433** when using the tunnel (step 2).
- Use your real password; do not commit `.env`.

**One-time: migrations and seed** (with tunnel running):

```powershell
.\scripts\run_migrations_and_seed.ps1
```

---

## 4. Start the backend API

From repo root, with `PYTHONPATH` set so the router can load `cdss`:

```powershell
cd d:\AI_Hackathon_CDSS
$env:PYTHONPATH = "src"
python scripts/run_api_local.py
```

You should see:

- `CDSS local API at http://localhost:8080`
- `Data source: database (DATABASE_URL/RDS)` ← means DB is connected

If you see **"Data source: mock data"**, the backend has no DB: check tunnel (step 2) and `DATABASE_URL` in `.env`.

---

## 5. Verify the API is running

**Local API:**

```powershell
# Health (should include "database": "connected" when DB is up)
Invoke-RestMethod -Uri http://localhost:8080/health

# Or raw body
(Invoke-WebRequest -Uri http://localhost:8080/health -UseBasicParsing).Content
```

**Deployed API (API Gateway):**

```powershell
Invoke-RestMethod -Uri "https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev/health"
```

Expected JSON includes `"service": "cdss"` and, for local with DB, `"database": "connected"`.

---

## 6. Start the frontend

After `.env.local` is correct (step 1), **restart** the dev server so Vite picks up env:

```powershell
cd frontend\apps\doctor-dashboard
npm run dev
```

Open the URL shown (e.g. `http://localhost:5173`). Hard refresh (Ctrl+Shift+R) if the banner or data is stale.

---

## Quick diagnostic commands

```powershell
# 1. Is the API reachable? (local)
(Invoke-WebRequest -Uri http://localhost:8080/health -UseBasicParsing -TimeoutSec 3).Content

# 2. Is anything listening on tunnel port?
Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue

# 3. Is the backend process running?
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*python*" }

# 4. Frontend env (must show VITE_API_URL without spaces)
Get-Content frontend\apps\doctor-dashboard\.env.local
```

---

## Alternative: use mock data

To develop the frontend without the backend or database:

In `frontend/apps/doctor-dashboard/.env.local`:

```env
VITE_USE_MOCK=true
```

Leave `VITE_API_URL` empty or set to any value. The app will use in-app mock data and the yellow banner will not show.

---

## Order of operations (summary)

| Order | Terminal | Command |
|-------|----------|---------|
| 1 | Terminal 1 | `.\scripts\start_ssh_tunnel.ps1` (keep open) |
| 2 | Terminal 2 | `.\scripts\run_migrations_and_seed.ps1` (one-time) |
| 3 | Terminal 2 | `$env:PYTHONPATH='src'; python scripts/run_api_local.py` |
| 4 | Terminal 3 | `cd frontend\apps\doctor-dashboard; npm run dev` |
| 5 | Browser | Open http://localhost:5173 and refresh |
