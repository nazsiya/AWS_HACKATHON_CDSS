# CDSS Implementation Status & Completion Guide

This document describes **what is already implemented** in the frontend, backend, and database, **what is incomplete or not wired**, and **why the dashboard may not be fully functional**. Use it as a single reference to fix issues and complete remaining work.

---

## 1. Quick Summary

| Layer        | Implemented | Incomplete / Not Wired | Notes |
|-------------|-------------|-------------------------|-------|
| **Frontend**| Core pages, API client, AIChat, Patients, Surgery, Resources, PatientConsultation, Admin (audit/config/analytics/users), Dashboard KPIs | Schedule & Appointments use **mock only**; Doctor’s Tasks always mock; some Admin endpoints show stub data | Set `VITE_API_URL` and `VITE_USE_MOCK=false` |
| **Backend** | All routes in FRONTEND_API_ENDPOINTS; `/dashboard`, `/agent`, `/api/v1/*`, `/api/ai/*`, Swagger UI | Cognito/SSM optional → users/config can be stub | Run `python scripts/run_api_local.py`; set `DATABASE_URL` for real data |
| **Database** | Schema (patients, visits, surgeries, resources, schedule_slots, medications, reminders, audit_log, etc.) | Requires migrations + `DATABASE_URL` or tunnel to Aurora | When DB unavailable, API uses mock/stub data |

**Most common reasons the dashboard “doesn’t work”:**

1. **Frontend not pointing to API** — `VITE_API_URL` empty or wrong; or `VITE_USE_MOCK=true` so all data is mock.
2. **Backend not running** — Local API not started, or deployed API unreachable (CORS/network).
3. **Database not connected** — No `DATABASE_URL` or tunnel → dashboard shows zeros, patients/surgeries from mock or empty.
4. **Schedule / Appointments** — These pages **never call the API**; they always use mock data (by design so far).

---

## 2. Frontend – What Exists and What’s Wired

### 2.1 Configuration

- **Location:** `frontend/apps/doctor-dashboard/.env` or `.env.local`
- **Variables:** `VITE_API_URL` (base URL, no trailing slash), `VITE_USE_MOCK` (`true`/`false`), optional `VITE_API_KEY`, optional Cognito vars.
- **Config module:** `src/api/config.js` — `config.apiUrl`, `isMockMode()`.
- When `VITE_USE_MOCK=false` and `VITE_API_URL` is set, the app calls the backend; otherwise it uses in-app mock data or fails with “Cannot reach API”.

### 2.2 API Client (`src/api/client.js`)

All functions below are implemented and used as follows:

| Function | Method | Endpoint | Used By | Notes |
|---------|--------|----------|---------|--------|
| `getDashboard(doctorId?)` | GET | `/dashboard` | Dashboard.jsx | KPIs (totalPatients, activeSurgeries) from API when not mock |
| `getPatients()` | GET | `/api/v1/patients` | Patients, Medications, PatientConsultation | List and context |
| `getPatient(id)` | GET | `/api/v1/patients/:id` | PatientConsultation | Detail + consultationHistory |
| `getSurgeries()` | GET | `/api/v1/surgeries` | Surgery.jsx | Surgery list |
| `getSurgery(id)` | GET | `/api/v1/surgeries/:id` | SurgeryPlanning (if used) | Single surgery |
| `getResources()` | GET | `/api/v1/resources` | Resources.jsx, AdminResources.jsx | Capacity + inventory |
| `getSchedule()` | GET | `/api/v1/schedule` | **Not used by any page** | Schedule.jsx uses mock only |
| `getMedications()` | GET | `/api/v1/medications` | **Not used** | Medications.jsx uses `getPatients()` only |
| `startConsultation(patientId, doctorId)` | POST | `/api/v1/consultations/start` | PatientConsultation.jsx | Start visit, get AI summary |
| `saveConsultation(patientId, body)` | POST | `/api/v1/consultations` | PatientConsultation.jsx | Save notes/transcript |
| `postAgent(body)` | POST | `/agent` | AIChat.jsx | AI Supervisor / Bedrock |
| `postSummarize(body)` | POST | `/api/ai/summarize` | (Ad-hoc) | AI summary |
| `sendNudge(patientId, medicationId)` | POST | `/api/v1/reminders/nudge` | (If used) | Nudge reminder |
| `scheduleReminder(...)` | POST | `/api/v1/reminders` | (If used) | Create reminder |
| `getUsers()` | GET | `/api/v1/admin/users` | AdminUsers.jsx | Cognito or stub |
| `getAuditLog(params)` | GET | `/api/v1/admin/audit` | AdminAudit.jsx | From audit_log |
| `getSystemConfig()` | GET | `/api/v1/admin/config` | AdminConfig.jsx | SSM or stub |
| `updateSystemConfig(body)` | PUT | `/api/v1/admin/config` | AdminConfig.jsx | SSM or in-memory |
| `getAnalytics()` | GET | `/api/v1/admin/analytics` | AdminAnalytics.jsx | OT utilisation, reminders, conflicts |
| `postActivityLog(body)` | POST | `/api/v1/activity` | ActivityContext | Doctor activity audit |

### 2.3 Pages – Implemented vs Mock-Only

| Page | API calls | Data source when not mock | Gaps / notes |
|------|-----------|----------------------------|--------------|
| **Dashboard** | `getDashboard()` | Backend `/dashboard` → stats from DB or stub | **Doctor’s Tasks** section always uses `pendingClinicalTasks` from mockData (not from API). KPIs (Total Patients, Surgery Schedules) come from API when `!isMockMode()` and API succeeds. |
| **Patients** | `getPatients()` | Backend `/api/v1/patients` | Works when API + DB are up. Handles both array and `data.patients`. |
| **PatientConsultation** | `getPatient()`, `startConsultation()`, `saveConsultation()` | Backend patients + consultations | Wired. AI summary from startConsultation when Bedrock configured. |
| **Surgery** | `getSurgeries()` | Backend `/api/v1/surgeries` | **“Find replacement”** panel uses `mockReplacements` (not `getSchedule` find-replacement API). |
| **AIChat** | `postAgent()` | Supervisor + Bedrock | Shows `safety_disclaimer`. Works when backend and Bedrock (or Nova fallback) are available. |
| **Resources** | `getResources()` | Backend `/api/v1/resources` | Expects `data.capacity` and `data.inventory` (or `data.items`). Backend returns both. |
| **Schedule** | **None** | **Mock only** (`todaySchedule`, `surgeries` from mockData) | **Not wired to API.** `getSchedule()` exists in client but is never called. |
| **Appointments** | **None** | **Mock only** (`adminAppointmentsList`) | **Not wired to API.** No backend appointments list endpoint used. |
| **Medications** | `getPatients()` only | Patient list from API | Does **not** call `getMedications()`; medication list from API is unused on this page. |
| **Admin Users** | `getUsers()` | Cognito or stub | May show empty list if Cognito not configured. |
| **Admin Audit** | `getAuditLog()` | `audit_log` table | Works when DB connected. |
| **Admin Config** | `getSystemConfig()`, `updateSystemConfig()` | SSM or in-memory stub | Works; may show “stub” message locally. |
| **Admin Analytics** | `getAnalytics()` | Aurora (schedule_slots, reminders) | Works when DB has data. |

### 2.4 Other Frontend Pieces

- **ApiHealthBanner:** Calls `GET /health`; shows a warning when `database !== 'connected'` (e.g. no tunnel or no `DATABASE_URL`).
- **Auth:** Login, ProtectedRoute, DoctorModuleGuard, PatientPortalGuard; role-based routes. Cognito optional; without it, role may come from mock or header.
- **Patient Portal:** Separate layout; can be restricted to single Patient_ID when RBAC is enforced.

---

## 3. Backend – What Exists and What Returns

### 3.1 Entry and Routing

- **Local server:** `scripts/run_api_local.py` — wraps the Lambda-style router. Paths:
  - **Without `/api/` prefix** (e.g. `/dashboard`, `/health`): sent as-is; router matches by `path`.
  - **With `/api/` prefix** (e.g. `/api/v1/patients`): `pathParameters.proxy` = `v1/patients`; router dispatches by `proxy`.
- **Router:** `src/cdss/api/handlers/router.py` — handles:
  - `GET /health` — health + `database: "connected" | "unavailable"`
  - `GET /dashboard` — dashboard handler
  - `POST /agent` — Supervisor (or Bedrock chat fallback)
  - `GET /docs/swagger.yaml`, `GET /api/docs` — Swagger spec and UI
  - `GET /api/v1/terminology` — approved terminology
  - Admin paths require `role === "admin"` (from claims).
  - Patient role: may only access own record; list all patients returns 403.

### 3.2 Handlers and Response Shapes

| Path / proxy | Handler | Response shape (success) | Notes |
|--------------|---------|---------------------------|--------|
| `GET /dashboard` | dashboard.py | `{ stats: { totalPatients, activeSurgeries, alertsCount }, patientQueue, aiAlerts, recentActivity }` | From DB or stub when DB unavailable. |
| `POST /agent` | supervisor.py → Bedrock or agent | `{ reply, safety_disclaimer, ... }` | Intent routing; fallback to simple chat. |
| `v1/patients` (GET/POST), `v1/patients/:id` (GET/PUT) | patient.py | List: `{ patients: [...] }`; detail: full patient + consultationHistory, aiSummary | ABDM stub optional; Bedrock summary when configured. |
| `v1/surgeries` (GET), `v1/surgeries/:id` (GET) | surgery.py | List/detail from DB | Joined with patient name. |
| `v1/resources` (GET) | resource.py | `{ ots, equipment, specialists, capacity, inventory, conflicts }` | Frontend uses `capacity` and `inventory`. |
| `v1/schedule` (GET/POST), find-replacement, notify-replacement, utilisation | scheduling.py | `{ schedule: [...] }`, etc. | Schedule page does not call GET yet. |
| `v1/medications` (GET/POST), `v1/reminders/*`, `v1/consultations/*` | engagement.py | Medications list, reminder ack, consultation start/save | Consultations create/update Visit. |
| `v1/admin/audit` | admin.py | `{ items: [...] }` | From `audit_log`. |
| `v1/admin/users` | admin.py | `{ users: [...] }` | From Cognito when pool ID set; else `[]` + stub message. |
| `v1/admin/config` (GET/PUT) | admin.py | Config JSON | SSM or in-memory fallback. |
| `v1/admin/analytics` | admin.py | `{ otUtilization, otConflicts, reminderStats, ... }` | From Aurora. |
| `v1/activity` (POST) | activity.py | `{ ok, ... }` | Writes to audit. |
| `v1/terminology` (GET) | router | `{ terminology, languages }` | Phase 3.4 / R7. |
| `ai/summarize`, `ai/entities`, `ai/surgery-support`, `ai/translate` | ai.py | Validated JSON + safety_disclaimer | Bedrock/Nova. |

### 3.3 Data Source When Database Unavailable

- If **DATABASE_URL** is not set (or DB unreachable), `run_api_local.py` can use a **mock session** (see script: `_mock_get_session`) so patients and surgeries return sample data.
- Dashboard handler uses `get_dashboard_data()`: on DB failure it returns **stub** (zeros, empty queues).
- Other handlers that need DB will fail or return empty/error unless similarly mocked.

---

## 4. Database – What Exists and What’s Required

### 4.1 Schema (src/cdss/db/models.py and migrations)

- **Tables used by frontend/API:**  
  `patients`, `medical_conditions`, `visits`, `surgeries`, `resources`, `schedule_slots`, `medications`, `reminders`, `audit_log`, `hospitals`, etc.
- **Alignment doc:** `docs/DATABASE_SCHEMA_FRONTEND_ALIGNMENT.md` — maps endpoints to tables and fields.
- **Reference DDL:** `backend/database/schema_frontend_alignment.sql` (and migrations under `src/cdss/db/migrations/`).

### 4.2 When Database Is “Connected”

- Backend sets `DATABASE_URL` (or RDS via Secrets Manager) and can reach PostgreSQL (e.g. via SSH tunnel to Aurora).
- `GET /health` returns `"database": "connected"`; otherwise `"unavailable"`.
- Dashboard, patients, surgeries, resources, schedule, medications, reminders, audit, analytics all read/write from Aurora/Postgres.

### 4.3 When Database Is Not Used

- No `DATABASE_URL` or connection failure → dashboard uses stub; patients/surgeries may come from local mock in `run_api_local.py` or error/empty.
- Frontend **ApiHealthBanner** shows “Backend is not connected to the database” when `database !== 'connected'`.

---

## 5. What’s Yet to Complete (Checklist)

### 5.1 Frontend

- [ ] **Schedule page** — Call `getSchedule()` and render backend `schedule`; optionally filter by date/OT.
- [ ] **Appointments page** — Define an appointments API (e.g. from visits/slots or dedicated table) and call it instead of `adminAppointmentsList`.
- [ ] **Medications page** — Use `getMedications()` for the medication list (and keep or add patient filter as needed).
- [ ] **Dashboard – Doctor’s Tasks** — Replace `pendingClinicalTasks` mock with an API (e.g. tasks from visits/surgeries/reminders) or remove if out of scope.
- [ ] **Surgery – Find replacement** — Call `POST /api/v1/schedule/find-replacement` (and optionally notify) instead of `mockReplacements`.
- [ ] **Error handling** — Ensure all pages show clear messages when API is down or returns 4xx/5xx (some already do; verify consistently).
- [ ] **Cognito** — If using real auth, set `VITE_COGNITO_*` and ensure backend receives role/claims; Admin Users will then list real users.

### 5.2 Backend

- [ ] **Appointments API** — If Appointments page should show real data, add e.g. `GET /api/v1/appointments` (from visits/slots or new table) and document in FRONTEND_API_ENDPOINTS + swagger.
- [ ] **Dashboard tasks** — Optional endpoint for “doctor’s tasks” (e.g. from visits, surgeries, reminders) if frontend is to drop mock.
- [ ] **Cognito / SSM** — Configure when moving off stub: Cognito User Pool for admin users; SSM for admin config.
- [ ] **RBAC** — Finalize Cognito (or IdP) groups for Doctor vs Patient; already enforced in router for patient-scoped access.

### 5.3 Database

- [ ] **Migrations** — Ensure all envs run `python -m cdss.db.migrations.run` (or equivalent) so schema matches models and frontend alignment doc.
- [ ] **Seed data** — Use seed script or manual data so dashboard, patients, surgeries, schedule have sample rows when testing without mock.
- [ ] **Appointments** — If adding appointments API, add or reuse tables (e.g. visits, schedule_slots) and document in schema alignment doc.

### 5.4 DevOps / Runbooks

- [ ] **Local run** — Document: 1) Start tunnel (if Aurora); 2) Set `DATABASE_URL` in repo root `.env`; 3) Start API (`PYTHONPATH=src python scripts/run_api_local.py`); 4) Set `VITE_API_URL` and `VITE_USE_MOCK=false` in frontend `.env.local`; 5) Start frontend (`npm run dev`).
- [ ] **Phase 4+** — Medical audit dashboard, RBAC tests, notifications (R9), performance (sub-2s), SLO/monitoring (see DEVELOPMENT_COMPLETION_STEPS.md).

---

## 6. How to Get the Dashboard “Working” Step by Step

1. **Backend**
   - From repo root: `$env:PYTHONPATH='src'; python scripts/run_api_local.py` (or set `PORT` if 8080 is in use).
   - Optional: set `DATABASE_URL` in repo root `.env` (and start SSH tunnel if DB is Aurora).

2. **Frontend**
   - In `frontend/apps/doctor-dashboard`: create or edit `.env.local` with:
     - `VITE_API_URL=http://localhost:8080` (or the port you used).
     - `VITE_USE_MOCK=false`.
   - Restart dev server: `npm run dev`; hard-refresh browser (Ctrl+Shift+R).

3. **Verify**
   - Open app; **ApiHealthBanner** should not show “not connected to database” if DB is connected.
   - **Dashboard:** Total Patients and Surgery Schedules should show numbers (from DB or stub).
   - **Patients:** List should load (from DB or mock from local server).
   - **AIChat:** Send a message; reply and safety disclaimer should appear if Bedrock/Nova is configured.

4. **If dashboard still shows zeros**
   - Check `GET http://localhost:8080/health` — if `database: "unavailable"`, fix `DATABASE_URL`/tunnel.
   - Check `GET http://localhost:8080/dashboard` — should return `{ stats: { totalPatients, activeSurgeries }, ... }`.
   - If API is on another port, ensure `VITE_API_URL` uses that port and that no other server is bound to 8080.

5. **If “Cannot reach API”**
   - Confirm backend is running and `VITE_API_URL` matches (no trailing slash).
   - Confirm `VITE_USE_MOCK` is not `true` when you want live API.
   - For deployed API from localhost, check CORS and optional `VITE_API_KEY`.

---

## 7. References

- **API contract:** `docs/swagger.yaml`; Swagger UI at `GET /api/docs`.
- **Frontend ↔ Backend mapping:** `docs/FRONTEND_API_ENDPOINTS.md`.
- **Env and URLs:** `docs/FRONTEND_API_AND_ENV.md`.
- **DB alignment and migrations:** `docs/DATABASE_SCHEMA_FRONTEND_ALIGNMENT.md`.
- **Phases and verification:** `docs/DEVELOPMENT_COMPLETION_STEPS.md`.

---

*This document is the single reference for implementation status and completion. Update it when wiring new endpoints or changing data flow.*
