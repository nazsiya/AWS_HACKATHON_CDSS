# Database Schema – Frontend API Alignment

This document verifies that the CDSS database schema fully supports all frontend operations defined in [FRONTEND_API_ENDPOINTS.md](./FRONTEND_API_ENDPOINTS.md). It covers database existence check, frontend requirements extraction, schema validation, and migration steps.

---

## Step 1: Verify Database Existence

### Option A: Python API (src/cdss) – Aurora via SSM tunnel

The **src/cdss** API uses **SQLAlchemy models** (`src/cdss/db/models.py`) and expects a PostgreSQL database (Aurora, reached via the bastion tunnel).

**Check if the database and schema exist:**

1. Start the SSM tunnel: `.\scripts\start_ssm_tunnel.ps1` (leave it open).
2. In another terminal:
   ```powershell
   $env:PYTHONPATH = "src"
   $env:DATABASE_URL = "postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"
   python -m cdss.db.check_db
   ```
   Use the Aurora master password and port **5433** (tunnel port).

- **Database: connected** — Connection OK.
- **CDSS schema: present** — All required tables exist; frontend can use the API.
- **CDSS schema: incomplete** — Run migrations (Step 5).

**If the database or schema does not exist:** Run migrations with the tunnel and `DATABASE_URL` set (see above), then run `python -m cdss.db.migrations.run`.

### Option B: Backend Lambda (backend/api/rest/database_crud.py)

The Lambda CRUD layer uses **backend/database/refined_schema.sql** (separate from src/cdss). For a local DB used by that Lambda:

```powershell
python scripts/local_db_setup.py
```

This creates database `cdssdb` and applies `refined_schema.sql` + seed data. The **frontend** when calling `/api/v1/*` is routed to **src/cdss** (API Gateway → router), so the schema that must exist for the documented frontend is the **cdss.db** schema (Option A).

---

## Step 2: Frontend Requirements (from FRONTEND_API_ENDPOINTS.md)

All request/response shapes and query parameters are derived from the frontend API client and handlers.

| Endpoint | Method | Request payload / query | Response shape | Backend handler |
|----------|--------|--------------------------|----------------|------------------|
| `/health` | GET | — | `{ "status": "ok" }` | (health check) |
| `/dashboard` | GET | `?doctor_id=` (optional) | `{ stats, patientQueue, aiAlerts, recentActivity }` | dashboard.py |
| `/api/v1/patients` | GET | — | `{ patients: [{ id, name, age, gender, bloodGroup, ward, severity, status, vitals, conditions, lastVisit }] }` | patient.py |
| `/api/v1/patients/:id` | GET | — | Patient detail + consultationHistory, medications, aiSummary | patient.py |
| `/api/v1/consultations/start` | POST | `{ patient_id, doctor_id }` | `{ message, ai_summary?, entities? }` | engagement.py |
| `/api/v1/consultations` | POST | `{ patient_id, notes?, ai_summary? }` | `{ message }` | engagement.py |
| `/agent` | POST | `{ message?, prompt? }` | `{ reply?, message?, safety_disclaimer? }` | supervisor / bedrock |
| `/api/v1/medications` | GET | — | `{ medications: [...] }` | engagement.py |
| `/api/v1/surgeries` | GET | — | `{ surgeries: [...] }` | surgery.py |
| `/api/v1/surgeries/:id` | GET | — | Single surgery detail | surgery.py |
| `/api/v1/resources` | GET | — | `{ resources: [...] }` or `{ ots, equipment, specialists }` | resource.py |
| `/api/v1/schedule` | GET | — | `{ schedule: [...] }` | scheduling.py |
| `/api/v1/reminders/nudge` | POST | `{ patient_id, medication_id? }` | `{ ok, message, notification? }` | engagement.py |
| `/api/v1/reminders` | POST | `{ patient_id, medication_id?, scheduled_at }` | `{ ok?, ... }` | engagement.py |
| `/api/v1/admin/users` | GET | — | `{ users: [...] }` | Cognito (no DB table) |
| `/api/v1/admin/audit` | GET | `?limit=` | `{ items: [{ id, user_id, user_email, action, resource, timestamp }] }` | admin.py → audit_log |
| `/api/v1/activity` | POST | `{ doctor_id, action, patient_id?, resource?, detail? }` | `{ ok, doctor_id, action, resource }` | activity.py → audit_log |
| `/api/v1/admin/config` | GET/PUT | — | Config JSON | SSM (no DB) |
| `/api/v1/admin/analytics` | GET | — | `{ otUtilization, otConflicts, reminderStats }` | admin.py → schedule_slots, reminders |

---

## Step 3: Entity → Table Mapping

| Entity | Table(s) | Key fields for frontend |
|--------|----------|--------------------------|
| Users | (Cognito) | — |
| Doctors | (Cognito / JWT) | — |
| Patients | `patients` | id, name, date_of_birth, gender, blood_group, ward, severity, status, vitals, conditions, last_visit |
| Patient medical records | `patients`, `visits`, `medications` | visits.notes, visits.summary, medications |
| Surgeries | `surgeries` | id, patient_id, type, surgeon_id, ot_id, scheduled_date, scheduled_time, status |
| Resources (OT, equipment, staff) | `resources` | id, type, name, status, availability |
| Scheduling | `schedule_slots` | id, ot_id, slot_date, slot_time, surgery_id, status |
| Conversations / AI summaries | `visits` | notes, summary, extracted_entities |
| Medication reminders | `reminders` | patient_id, medication_id, reminder_at, sent_at |
| Audit logs | `audit_log` | user_id, user_email, action, resource, timestamp, details |

---

## Step 4: Required Tables and Fields

All frontend endpoints are served by **src/cdss/api/handlers/** using **src/cdss/db/models.py**.

### Tables that must exist

| Table | Purpose | Frontend endpoints |
|-------|---------|--------------------|
| `patients` | Patient records | /api/v1/patients, consultations, medications, schedule |
| `visits` | Consultations | Patient detail (consultationHistory), POST consultations |
| `surgeries` | Surgery plans | /api/v1/surgeries, /api/v1/surgeries/:id, dashboard, schedule |
| `resources` | OTs, equipment, staff | /api/v1/resources |
| `schedule_slots` | Booked slots | /api/v1/schedule, admin/analytics |
| `medications` | Prescriptions | /api/v1/medications, reminders |
| `reminders` | Medication reminders | POST reminders, nudge; admin/analytics |
| `audit_log` | Audit + doctor activity | GET admin/audit, POST /api/v1/activity, dashboard |
| `hospitals` | Hospital registry | /api/v1/hospitals (if used) |

### Foreign keys (referential integrity)

- `visits.patient_id` → `patients.id` (CASCADE)
- `surgeries.patient_id` → `patients.id` (CASCADE)
- `schedule_slots.surgery_id` → `surgeries.id` (SET NULL)
- `medications.patient_id` → `patients.id` (CASCADE)
- `reminders.patient_id` → `patients.id` (CASCADE); `reminders.medication_id` → `medications.id` (SET NULL)

---

## Step 5: Create or Update Schema

### Database does not exist

1. Create PostgreSQL database `cdssdb`.
2. Set `DATABASE_URL` and run:
   ```powershell
   $env:PYTHONPATH = "src"
   python -m cdss.db.migrations.run
   ```
   This creates all tables from **models.py** via `Base.metadata.create_all()`.

### Database exists but schema incomplete

1. Run the same command; `create_all()` adds missing tables.
2. Apply incremental migrations in **src/cdss/db/migrations/** (002, 003, 004) if your DB was created from older SQL.
3. Integer PK tables get sequences via `_ensure_serial_defaults` in run.py (audit_log, visits, schedule_slots, medications, reminders).

---

## Step 6: Data Integrity

- **Foreign keys:** Enforced in models and in **backend/database/schema_frontend_alignment.sql**.
- **Indexes:** On patient_id, doctor_id, surgeon_id, ot_id, user_id, timestamp for performance.

---

## Step 7: Output Summary

### Confirmation

- **Database existed or newly created:** Use `python -m cdss.db.check_db` to confirm. If missing, create DB and run `python -m cdss.db.migrations.run`.
- **Schema changes made:** None to models.py; it already supports all frontend endpoints. **004_frontend_alignment.sql** adds missing columns (e.g. `visits.extracted_entities`, `audit_log.resource` NOT NULL) for DBs created from 001/002/003—run it manually if needed. **backend/database/schema_frontend_alignment.sql** is the reference DDL matching models.py for creating the DB from scratch with raw SQL. Note: `python -m cdss.db.migrations.run` uses SQLAlchemy `create_all()` and does not run the 001–004 `.sql` files.
- **Updated schema:** See **backend/database/schema_frontend_alignment.sql** for full SQL. After applying it or migrations, run `python -m cdss.db.check_db` to verify.
