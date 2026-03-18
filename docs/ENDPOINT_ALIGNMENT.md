# Frontend–Backend Endpoint Alignment & Production Readiness

**Purpose:** Confirm every frontend API call has a connected backend route and is documented in OpenAPI. Use this before production deployment.

**References:** `docs/FRONTEND_API_ENDPOINTS.md`, `docs/OPENAI_API_ENDPOINTS.md`, `docs/swagger.yaml`, `frontend/apps/doctor-dashboard/src/api/client.js`, `src/cdss/api/handlers/router.py`.

---

## 1. Alignment Summary

| Source | Count | Status |
|--------|--------|--------|
| **Frontend client.js** | All exported functions | ✅ Mapped to backend |
| **Backend router** | All `/api/*` and `/agent`, `/dashboard`, `/health` | ✅ Dispatched to handlers |
| **swagger.yaml** | OpenAPI 3.0 paths | ✅ Includes all frontend-used + AI endpoints |
| **FRONTEND_API_ENDPOINTS.md** | Frontend → endpoint → handler | ✅ Updated |
| **OPENAI_API_ENDPOINTS.md** | AI endpoints + supervisor | ✅ Updated |

---

## 2. Endpoint Checklist (Frontend → Backend → Swagger)

### Core & Dashboard
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| getDashboard | GET /dashboard | path.endswith("/dashboard") | dashboard.get_dashboard_data | ✅ /dashboard |
| getPatients | GET /api/v1/patients | v1/patients | patient | ✅ /api/v1/patients |
| getPatient(id) | GET /api/v1/patients/:id | v1/patients | patient | ✅ /api/v1/patients/{id} |
| getMedications | GET /api/v1/medications | v1/medications | engagement | ✅ /api/v1/medications |
| getSurgeries | GET /api/v1/surgeries | v1/surgeries | surgery | ✅ /api/v1/surgeries |
| getSurgery(id) | GET /api/v1/surgeries/:id | v1/surgeries | surgery | ✅ /api/v1/surgeries/{id} |

### Consultations & Agent
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| startConsultation | POST /api/v1/consultations/start | v1/consultations | engagement | ✅ /api/v1/consultations/start |
| saveConsultation | POST /api/v1/consultations | v1/consultations | engagement | ✅ /api/v1/consultations |
| postSummarize | POST /api/ai/summarize | ai/* | ai | ✅ /api/ai/summarize |
| postAgent | POST /agent | path.endswith("/agent") | supervisor | ✅ /agent |

### AI (Phase 2B+)
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| postAiPrescription | POST /api/ai/prescription | ai/* | ai | ✅ /api/ai/prescription |
| postAiAdherence | POST /api/ai/adherence | ai/* | ai | ✅ /api/ai/adherence |
| postAiEngagement | POST /api/ai/engagement | ai/* | ai | ✅ /api/ai/engagement |
| postAiResources | POST /api/ai/resources | ai/* | ai | ✅ /api/ai/resources |

### Operations
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| getResources | GET /api/v1/resources | v1/resources | resource | ✅ /api/v1/resources |
| getSchedule | GET /api/v1/schedule | v1/schedule | scheduling | ✅ /api/v1/schedule |
| sendNudge | POST /api/v1/reminders/nudge | v1/reminders | engagement | ✅ /api/v1/reminders/nudge |
| scheduleReminder | POST /api/v1/reminders | v1/reminders | engagement | ✅ /api/v1/reminders |
| postActivityLog | POST /api/v1/activity | v1/activity | activity | ✅ /api/v1/activity |

### Appointments & Tasks
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| getAppointments | GET /api/v1/appointments | v1/appointments | appointments | ✅ /api/v1/appointments |
| createAppointment | POST /api/v1/appointments | v1/appointments | appointments | ✅ /api/v1/appointments |
| getTasks | GET /api/v1/tasks | v1/tasks | tasks | ✅ /api/v1/tasks |

### Admin
| Frontend | Endpoint | Router | Handler | Swagger |
|----------|----------|--------|---------|---------|
| getUsers | GET /api/v1/admin/users | v1/admin | admin | ✅ /api/v1/admin/users |
| getAuditLog | GET /api/v1/admin/audit | v1/admin | admin | ✅ /api/v1/admin/audit |
| getSystemConfig | GET /api/v1/admin/config | v1/admin | admin | ✅ /api/v1/admin/config |
| updateSystemConfig | PUT /api/v1/admin/config | v1/admin | admin | ✅ /api/v1/admin/config |
| getAnalytics | GET /api/v1/admin/analytics | v1/admin | admin | ✅ /api/v1/admin/analytics |

### Other
| Use | Endpoint | Router | Swagger |
|-----|----------|--------|---------|
| Health / ApiHealthBanner | GET /health | path.endswith("/health") | ✅ /health |
| Terminology (R7) | GET /api/v1/terminology | v1/terminology | ✅ /api/v1/terminology |
| Swagger UI | GET /api/docs | proxy==docs | (served by router) |
| OpenAPI spec | GET /docs/swagger.yaml | path==/docs/swagger.yaml | (served by router) |

---

## 3. Production Readiness

- **All frontend client methods** have a corresponding backend route and handler.
- **All routes** are documented in `docs/swagger.yaml` with request/response shapes where applicable.
- **AI endpoints** return validated JSON and include `safety_disclaimer` per project conventions.
- **RBAC:** Admin paths require `role === "admin"`; patient role is restricted to own record (router enforces).
- **CORS:** Enabled in backend for API Gateway and local dev.

**Verdict:** Endpoints are aligned and **ready for production deployment** from a contract perspective. Proceed with infra deploy (`.\scripts\deploy.ps1`), then frontend deploy (`.\scripts\deploy_frontend.ps1`) with correct `VITE_API_URL` at build time.

---

## 4. Quick Verification (Local)

With backend running (`python scripts/run_api_local.py`) and frontend using `VITE_API_URL=http://localhost:8080`, `VITE_USE_MOCK=false`:

1. **Health:** `curl -s http://localhost:8080/health` → `service`, `status`, `database`
2. **Patients:** `curl -s http://localhost:8080/api/v1/patients` → `patients` array or mock
3. **Agent:** `curl -s -X POST http://localhost:8080/agent -H "Content-Type: application/json" -d "{\"message\":\"list patients\"}"` → `reply`, `safety_disclaimer`
4. **AI summarize:** `curl -s -X POST http://localhost:8080/api/ai/summarize -H "Content-Type: application/json" -d "{\"text\":\"Patient has fever.\"}"` → `summary`, `safety_disclaimer`
5. **Swagger UI:** Open `http://localhost:8080/api/docs` → spec loads

See also `scripts/verify_phase3_connectivity.py` and `scripts/verify_phase4_ai.py`.
