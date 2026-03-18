# CDSS Frontend API Endpoints (Req 7.2)

This document maps the React frontend API client (`client.js`) functions to the corresponding backend REST endpoints. All endpoints are implemented in the backend router and handlers; see `docs/swagger.yaml` for the full OpenAPI spec.

## 1. Core Clinical Data

| Frontend Function | Method | Endpoint | Backend Handler | Description |
| :--- | :--- | :--- | :--- | :--- |
| `getDashboard()` | `GET` | `/dashboard` | dashboard | Aggregate stats & queue. |
| `getPatients()` | `GET` | `/api/v1/patients` | patient | All patients list. |
| `getPatient(id)` | `GET` | `/api/v1/patients/:id` | patient | Full record + AI summary. |
| `getMedications()` | `GET` | `/api/v1/medications` | engagement | Global medication list. |
| `getSurgeries()` | `GET` | `/api/v1/surgeries` | surgery | Surgery list. |
| `getSurgery(id)` | `GET` | `/api/v1/surgeries/:id` | surgery | Single surgery. |

## 2. Consultations & AI

| Frontend Function | Method | Endpoint | Backend Handler | Description |
| :--- | :--- | :--- | :--- | :--- |
| `startConsultation()` | `POST` | `/api/v1/consultations/start` | engagement | Creates a new visit record. |
| `saveConsultation()` | `POST` | `/api/v1/consultations` | engagement | Updates notes and transcript. |
| `postSummarize(body)` | `POST` | `/api/ai/summarize` (fallback `/api/v1/ai/summarize`) | ai | Ad-hoc text/conversation summarization. |
| `postAgent(body)` | `POST` | `/agent` | supervisor | AI Supervisor interaction. |
| `postAiPrescription(body)` | `POST` | `/api/ai/prescription` | ai | AI-suggested prescription. |
| `postAiAdherence(body)` | `POST` | `/api/ai/adherence` | ai | Medication adherence analysis. |
| `postAiEngagement(body)` | `POST` | `/api/ai/engagement` | ai | Patient engagement scoring. |
| `postAiResources(body)` | `POST` | `/api/ai/resources` | ai | Health education resources. |

## 3. Operations & Safety

| Frontend Function | Method | Endpoint | Backend Handler | Description |
| :--- | :--- | :--- | :--- | :--- |
| `getResources()` | `GET` | `/api/v1/resources` | resource | OT & Equipment status. |
| `getSchedule()` | `GET` | `/api/v1/schedule` | scheduling | Staff & OT calendar. |
| `sendNudge(pId, mId)` | `POST` | `/api/v1/reminders/nudge` | engagement | Immediate SNS notification. |
| `scheduleReminder(...)` | `POST` | `/api/v1/reminders` | engagement | Schedule reminder. |
| `postActivityLog()` | `POST` | `/api/v1/activity` | activity | Record doctor interactions. |

## 4. Appointments & Tasks

| Frontend Function | Method | Endpoint | Backend Handler | Description |
| :--- | :--- | :--- | :--- | :--- |
| `getAppointments()` | `GET` | `/api/v1/appointments` | appointments | List appointments (from visits). |
| `createAppointment(body)` | `POST` | `/api/v1/appointments` | appointments | Create appointment (visit). |
| `getTasks()` | `GET` | `/api/v1/tasks` | tasks | Pending clinical tasks for dashboard. |

## 5. Admin (Phase 10)

| Frontend Function | Method | Endpoint | Backend Handler | Description |
| :--- | :--- | :--- | :--- | :--- |
| `getUsers()` | `GET` | `/api/v1/admin/users` | admin | List clinical staff. |
| `getAuditLog()` | `GET` | `/api/v1/admin/audit` | admin | Compliance logs (Admin only). |
| `getSystemConfig()` | `GET` | `/api/v1/admin/config` | admin | Read Parameter Store values. |
| `updateSystemConfig(body)` | `PUT` | `/api/v1/admin/config` | admin | Update system config. |
| `getAnalytics()` | `GET` | `/api/v1/admin/analytics` | admin | Admin analytics. |

## 6. Other

| Frontend / Backend | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| Health check | `GET` | `/health` | Service and database status. |
| Terminology | `GET` | `/api/v1/terminology` | Approved medical terminology (R7). |

---
*VITE_API_URL: http://localhost:8080 (Local) | API Gateway URL (Deployed)*  
*Mock Mode: VITE_USE_MOCK=false for live API.*  
*OpenAPI: `docs/swagger.yaml`; Swagger UI: GET /api/docs*
