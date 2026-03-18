# Frontend data fetch and API / DB URLs

## How the dashboard gets patients and surgery data

1. **Config**  
   The app reads `VITE_API_URL` and `VITE_USE_MOCK` from env (see below). All API calls use `config.apiUrl` from `frontend/apps/doctor-dashboard/src/api/config.js`.

2. **API client**  
   `src/api/client.js` builds the request URL as `${config.apiUrl}${path}` and sends:
   - **Patients:** `GET /api/v1/patients` → `getPatients()` → used by Patients page and Dashboard (when not mock).
   - **Surgeries:** `GET /api/v1/surgeries` → `getSurgeries()` → Surgery and Schedule pages.
   - **Dashboard:** `GET /dashboard` → `getDashboard()` → Dashboard KPIs (totalPatients, activeSurgeries).

3. **Flow**  
   Browser → `fetch(config.apiUrl + path)` → backend (local or API Gateway) → backend uses **DATABASE_URL** (backend-only) to query the DB → JSON response → frontend renders.

**DATABASE_URL** is **not** used by the frontend. It is used only by the **backend** (run_api_local.py or Lambda) to connect to PostgreSQL. The frontend only needs **VITE_API_URL** pointing to that backend.

---

## Where to set URLs and keys

### Frontend (doctor-dashboard)

**Location:** `frontend/apps/doctor-dashboard/`  
Create or edit **`.env`** and/or **`.env.local`** in that folder (Vite does **not** read the repo root `.env` for the dashboard).

| Variable         | Purpose |
|------------------|--------|
| `VITE_API_URL`   | Base URL of the REST API. No trailing slash. |
| `VITE_USE_MOCK`  | `true` or `1` = use in-app mock data; otherwise the app calls the API. |
| `VITE_API_KEY`   | Optional. If your API Gateway requires an API key, set it here; the client sends it as `x-api-key`. |

**Local development (backend on your machine):**

```env
VITE_API_URL=http://localhost:8080
VITE_USE_MOCK=false
```

**Deployed API (AWS API Gateway):**

```env
VITE_API_URL=https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev
VITE_USE_MOCK=false
# Optional if Gateway requires an API key:
# VITE_API_KEY=your-api-key-here
```

After changing any of these, **restart the dev server** (`npm run dev`) and hard-refresh the browser (Ctrl+Shift+R).

---

## Backend and DATABASE_URL

**Location:** repo root **`.env`** (used by `scripts/run_api_local.py` and backend code).

| Variable        | Purpose |
|-----------------|--------|
| `DATABASE_URL`  | PostgreSQL connection string for the **backend**. For local dev with SSH tunnel: `postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb`. Port **5433** is the local tunnel port; the tunnel forwards to Aurora. |

- **Frontend** never sees or uses `DATABASE_URL`.
- **Backend** uses it to connect to the DB. If it’s wrong or the tunnel is down, the API will return errors or `"database": "unavailable"` on `/health`.

**Correct pattern for local dev:**

1. Start SSH tunnel (e.g. `.\scripts\start_ssh_tunnel.ps1`).
2. In repo root `.env`: `DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb`.
3. Start backend: `$env:PYTHONPATH='src'; python scripts/run_api_local.py`.
4. In **frontend** `frontend/apps/doctor-dashboard/.env.local`: `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false`.
5. Start frontend: `npm run dev` from `frontend/apps/doctor-dashboard`.

---

## AWS API Gateway URL and reachability

- **URL:** `https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev`
- **Reachability:** A direct request to `/health` returns `200` with `{"status":"ok","service":"cdss"}`. So the endpoint is reachable from the network.
- **From the browser:** If you still see “Cannot reach API at https://b1q9qcuqia...”, common causes are:
  1. **CORS:** The browser may block the response if the API does not allow your frontend origin. API Gateway must be configured to allow your origin (e.g. `http://localhost:5173` for dev).
  2. **Wrong URL in the app:** The app may be using an old build or env. Ensure `VITE_API_URL` is set in `frontend/apps/doctor-dashboard/.env` or `.env.local`, restart `npm run dev`, and hard-refresh.
  3. **Using deployed API from localhost:** For local development, prefer `VITE_API_URL=http://localhost:8080` and run the backend locally so you don’t depend on the deployed API or CORS.

**API key:** The CDSS API Gateway may or may not require an `x-api-key` header. If you get 403 when calling the deployed URL, add `VITE_API_KEY=your-key` in `frontend/apps/doctor-dashboard/.env.local`. The client sends it as `x-api-key` when `config.apiKey` is set.

---

## Summary

| What you want           | Frontend env (in `frontend/apps/doctor-dashboard/`) | Backend / DB |
|-------------------------|------------------------------------------------------|--------------|
| Local dev, real data    | `.env` and `.env.local`: `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false` | Repo root `.env`: `DATABASE_URL=postgresql://...@localhost:5433/cdssdb`; run tunnel + `run_api_local.py` |
| Deployed API            | `VITE_API_URL=https://b1q9qcuqia.execute-api.ap-south-1.amazonaws.com/dev`, optional `VITE_API_KEY` | Backend and DB are on AWS; no local DATABASE_URL needed for frontend. |
| Mock data only          | `VITE_USE_MOCK=true` (no backend needed)             | Not needed. |
