# CDSS Backend API Reference
**Version:** Production (Phases 1–10) | **Region:** `ap-south-1` (Mumbai) | **Protocol:** HTTPS / REST over AWS API Gateway

---

## Deployment Architecture

```
Browser / Mobile App
        │
        ▼
  CloudFront (CDN)
        │
        ▼
 API Gateway (REST)  ◄──── Cognito User Pool (JWT auth)
        │
        ▼
 Lambda: cdss-router     ◄── Single entry-point / RBAC / Audit
        │
        ├── /dashboard            → dashboard.py
        ├── /agent                → supervisor.py
        ├── /api/v1/patients/*    → patient.py
        ├── /api/v1/surgeries/*   → surgery.py
        ├── /api/v1/resources     → resource.py
        ├── /api/v1/schedule/*    → scheduling.py
        ├── /api/v1/medications   → engagement.py
        ├── /api/v1/reminders/*   → engagement.py
        ├── /api/v1/consultations/* → engagement.py
        ├── /api/v1/supervisor    → supervisor.py
        ├── /api/v1/hospitals     → hospitals.py
        ├── /api/v1/triage        → triage.py (CDSS severity assessment; not a separate agent)
        └── /api/v1/admin/*       → admin.py
                 │
                 ▼
        Amazon Aurora PostgreSQL
        Amazon Bedrock (Claude)
        Amazon Translate / Comprehend
        Amazon SNS (notifications)
        Amazon S3 (transcripts)
        Amazon Cognito (RBAC)
```

### Base URL
```
https://<API_GATEWAY_ID>.execute-api.ap-south-1.amazonaws.com/prod
```
> Retrieve from: `gateway_config.json` or Terraform outputs.

---

## Authentication

All requests **must** include a Cognito JWT `Authorization` header:

```http
Authorization: Bearer <id_token>
```

Tokens are obtained via the Cognito Hosted UI or `aws cognito-idp initiate-auth`. The router extracts and enforces role from the JWT claim `custom:role`.

| Role | Access Level |
|------|-------------|
| `admin` | All endpoints including /api/v1/admin/* |
| `superuser` | Full access: same as admin, plus bypasses patient-scope restrictions (can list all patients and access any patient record) |
| `doctor` / `nurse` | All non-admin endpoints |
| `patient` | Own record only (`/api/v1/patients/:own-id`) |

---

## Multilingual Support (Phase 8)

All endpoints support localization via:
- **Query param:** `?lang=hi` (or `ta`, `te`, `bn`, `en`)
- **Header:** `Accept-Language: hi-IN,hi;q=0.9`

Patient-facing responses (reminders, nudges) are **auto-translated** to the patient's `language` field using Amazon Translate → Bedrock fallback.

---

## Endpoints

### 1. Dashboard  
**`GET /dashboard`**

Returns aggregate stats for the staff portal home screen. No patient-level data.

**Response:**
```json
{
  "stats": {
    "totalPatients": 42,
    "activeSurgeries": 8,
    "alertsCount": 3
  },
  "patientQueue": [],
  "aiAlerts": [],
  "recentActivity": [
    { "action": "GET /api/v1/patients", "resource": "/api/v1/patients", "timestamp": "2026-03-05T06:00:00Z" }
  ]
}
```

---

### 2. AI Supervisor Agent  
**`POST /agent`** *(also: `POST /api/v1/supervisor`)*

Natural-language interface. Automatically classifies intent and delegates to the right sub-agent. Supports multilingual input/output.

**Request:**
```json
{
  "message": "Show me the surgery checklist for SRG-1001",
  "patient_id": "PT-1001",
  "context": {}
}
```

**Response:**
```json
{
  "intent": "surgery",
  "agent": "surgery_agent",
  "data": { "...agent-specific response..." },
  "safety_disclaimer": "AI is for clinical support only...",
  "source": "local",
  "duration_ms": 342
}
```

**Intent labels:** `patient`, `surgery`, `resource`, `scheduling`, `engagement`, `hospitals`, `triage` (CDSS severity assessment), `general`  
**`source`:** `local` (keyword/Bedrock) or `agentcore` (when `USE_AGENTCORE=true`)

---

### 3. Patients

#### `GET /api/v1/patients`
List all patients. Sorted by `updated_at` descending.

**Response:**
```json
{
  "patients": [
    {
      "id": "PT-1001",
      "name": "Arjun Sharma",
      "age": 45,
      "gender": "male",
      "bloodGroup": "O+",
      "ward": "Cardiology",
      "severity": "high",
      "status": "admitted",
      "vitals": { "bp": "120/80", "hr": 72 },
      "conditions": ["hypertension", "diabetes"],
      "lastVisit": "2026-02-15",
      "nextAppointment": null
    }
  ]
}
```

---

#### `GET /api/v1/patients/:id`
Full patient detail. Includes consultation history, ABDM record (when configured), and Bedrock AI summary.

**Response:**
```json
{
  "id": "PT-1001",
  "name": "Arjun Sharma",
  "dateOfBirth": "1981-05-12",
  "age": 45,
  "gender": "male",
  "bloodGroup": "O+",
  "ward": "Cardiology",
  "severity": "high",
  "status": "admitted",
  "vitals": {},
  "conditions": ["hypertension"],
  "medications": [],
  "lastVisit": "2026-02-15",
  "nextAppointment": null,
  "surgeryReadiness": {},
  "aiSummary": "Patient has well-controlled hypertension...",
  "consultationHistory": [
    {
      "id": 5,
      "date": "2026-02-15",
      "doctor": "DR-201",
      "notes": "Follow-up visit",
      "aiSummary": "...",
      "prescriptions": []
    }
  ],
  "abdm": { "...ABDM record if configured..." }
}
```

---

#### `POST /api/v1/patients`
Create a new patient. ID is auto-generated (`PT-XXXX`).

**Request:**
```json
{
  "name": "Priya Nair",
  "dateOfBirth": "1990-08-20",
  "gender": "female",
  "language": "ta",
  "bloodGroup": "B+",
  "ward": "General",
  "severity": "medium",
  "status": "outpatient",
  "conditions": ["asthma"],
  "allergies": ["penicillin"],
  "abhaId": "ABHA-123456",
  "vitals": { "bp": "110/70", "hr": 80 },
  "address": { "city": "Chennai" },
  "emergencyContact": { "name": "Rajan Nair", "phone": "+91-9876543210" }
}
```

**Response:** `201` — full patient object (same as GET detail, without consultationHistory).

---

#### `PUT /api/v1/patients/:id`
Update patient fields. Only provided fields are updated (partial update).

**Request:** Any subset of the POST body fields.

**Response:** `200` — updated patient object.

---

### 4. Surgeries

#### `GET /api/v1/surgeries`
List all surgeries with patient name.

**Response:**
```json
{
  "surgeries": [
    {
      "id": "SRG-1001",
      "patient": "Arjun Sharma",
      "patient_id": "PT-1001",
      "type": "cardiac",
      "status": "scheduled",
      "scheduledDate": "2026-03-10",
      "surgeon": "DR-201",
      "ot": "OT-1",
      "complexity": "high",
      "checklist": [
        { "id": 1, "text": "Patient identity verified", "completed": false }
      ],
      "requiredInstruments": ["scalpel", "retractor"]
    }
  ]
}
```

---

#### `GET /api/v1/surgeries/:id`
Single surgery with full checklist and required instruments.

**Response:** Same shape as list item but with complete checklist populated.

---

#### `POST /api/v1/surgeries`
Create a surgery.

**Request:**
```json
{
  "patient_id": "PT-1001",
  "type": "cardiac",
  "scheduled_date": "2026-03-10",
  "surgeon_id": "DR-201",
  "ot_id": "OT-1",
  "status": "scheduled",
  "notes": "High-risk, requires senior review",
  "requirements": { "complexity": "high", "instruments": ["scalpel"] }
}
```

**Response:** `201` — created surgery object.

---

#### `PUT /api/v1/surgeries/:id`
Update surgery (including checklist completion status).

**Request:**
```json
{
  "status": "in_progress",
  "checklist": [{ "id": 1, "text": "Patient identity verified", "completed": true }]
}
```

---

#### `POST /api/v1/surgeries/:id/analyse`
Trigger Bedrock AI analysis: generates checklist, risk factors, and requirements for the surgery. Result is stored back to the surgery record.

**Request:** No body required.

**Response:**
```json
{
  "surgery_id": "SRG-1001",
  "pre_op_status": "ready",
  "checklist_flags": ["consent_signed", "fasting_confirmed"],
  "risk_factors": ["age > 60", "hypertension"],
  "requires_senior_review": true,
  "safety_disclaimer": "AI is for clinical support only..."
}
```

---

### 5. Resources

#### `GET /api/v1/resources`
Returns OTs, equipment, staff, inventory, and detected conflicts from Aurora.

**Response:**
```json
{
  "ots": [
    { "id": "OT-1", "name": "OT 1", "status": "available", "nextMaintenance": null }
  ],
  "equipment": [
    { "id": "EQ-1", "name": "Ventilator", "status": "available", "quantity": 3 }
  ],
  "specialists": [
    { "id": "DR-201", "name": "Dr. Patel", "specialty": "Cardiology", "status": "available" }
  ],
  "capacity": { "totalOTs": 5, "availableOTs": 3, "utilizationRate": 40 },
  "inventory": [
    { "id": "EQ-1", "name": "Ventilator", "specialty": "ICU", "status": "available", "assignedTo": null, "area": null }
  ],
  "conflicts": [
    { "ot_id": "OT-1", "date": "2026-03-10", "time": "09:00", "surgery_ids": ["SRG-1001", "SRG-1002"], "message": "OT OT-1 double-booked..." }
  ]
}
```

---

### 6. Scheduling

#### `GET /api/v1/schedule`
List all schedule slots (linked to surgeries and OTs).

**Response:**
```json
{
  "schedule": [
    {
      "id": 1,
      "ot": "OT-1",
      "date": "2026-03-10",
      "time": "09:00",
      "surgeryId": "SRG-1001",
      "patient": "Arjun Sharma",
      "status": "booked"
    }
  ]
}
```

---

#### `POST /api/v1/schedule`
Book a schedule slot. Returns `409` if the slot is already booked (also publishes SNS escalation alert).

**Request:**
```json
{
  "ot_id": "OT-1",
  "slot_date": "2026-03-10",
  "slot_time": "09:00",
  "surgery_id": "SRG-1001"
}
```

**Response:** `201` (new slot) or `200` (updated existing). Body: `{ "schedule": [slot], "message": "Slot booked" }`.

---

#### `POST /api/v1/schedule/find-replacement`
Find available replacement staff/doctors. Returns candidates from the `resources` table (type=staff).

**Request:**
```json
{ "doctor_id": "DR-201", "surgery_id": "SRG-1001", "date": "2026-03-10" }
```

**Response:**
```json
{
  "replacements": [
    { "id": "DR-202", "name": "Dr. Kumar", "specialty": "Cardiology", "status": "available" }
  ],
  "surgery_id": "SRG-1001",
  "date": "2026-03-10",
  "message": "Use Notify to send replacement request..."
}
```

---

#### `POST /api/v1/schedule/notify-replacement`
Publish a replacement request to the SNS `doctor-escalations` topic. Returns `trace_id` for audit.

**Request:**
```json
{ "surgery_id": "SRG-1001", "doctor_id": "DR-201" }
```

**Response:**
```json
{ "notified": true, "surgery_id": "SRG-1001", "trace_id": "uuid-...", "message": "..." }
```

---

#### `GET /api/v1/schedule/utilisation`
OT utilisation metrics per date.

**Response:**
```json
{
  "utilisation": [
    { "ot_id": "OT-1", "date": "2026-03-10", "slots_total": 8, "slots_booked": 5, "utilisation_pct": 62.5 }
  ]
}
```

---

### 7. Medications

#### `GET /api/v1/medications`
List all medications with patient name.

**Response:**
```json
{
  "medications": [
    {
      "id": "MED-1",
      "patient": "Arjun Sharma",
      "medication": "Metformin 500mg",
      "frequency": "twice daily",
      "nextDose": "2026-03-05T14:00:00+05:30",
      "status": "active",
      "interactions": []
    }
  ]
}
```

---

#### `POST /api/v1/medications`
Prescribe a new medication with automated drug interaction screening (Req 5.1).

**Request:**
```json
{
  "patient_id": "PT-1001",
  "medication_name": "Aspirin",
  "frequency": "once daily"
}
```

**Response (201):**
```json
{
  "ok": true,
  "medicationId": 15,
  "interactions": [
    { "severity": "high", "warning": "Increased bleeding risk with current Warfarin" }
  ],
  "alert_ids": ["uuid-alert-001"]
}
```

---

### 14. Clinical Alerts (Phase 5)

#### `GET /api/v1/alerts` (Planned)
Historical log of clinical and safety alerts for a patient.

#### Automated Triggers
- **Critical Vitals**: Heart Rate > 130, SpO2 < 90%, or BP Sys > 190 triggers a `critical` alert.
- **Drug Interactions**: High-severity interactions automatically emit an alert.
- **Escalation**: All critical alerts initiate an multi-channel escalation sequence (APP -> SMS -> Voice).

### 8. Reminders

#### `POST /api/v1/reminders`
Create a reminder in DB and publish SNS notification (translated to patient's language).

**Request:**
```json
{
  "patient_id": "PT-1001",
  "medication_id": 5,
  "scheduled_at": "2026-03-06T08:00:00Z"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Reminder scheduled",
  "notification": { "success": true, "message_id": "...", "trace_id": "..." }
}
```

---

#### `POST /api/v1/reminders/nudge`
Send an immediate medication nudge to a patient. Translates message to patient's preferred language and publishes to SNS `patient-reminders` topic.

**Request:**
```json
{ "patient_id": "PT-1001", "medication_id": 5 }
```

**Response:**
```json
{
  "ok": true,
  "message": "Nudge sent",
  "notification": { "success": true, "message_id": "...", "trace_id": "..." }
}
```

---

#### `GET /api/v1/reminders/adherence?patient_id=PT-1001`
Adherence statistics for a patient.

**Response:**
```json
{
  "patient_id": "PT-1001",
  "reminders_total": 30,
  "reminders_sent": 25,
  "reminders_overdue": 5,
  "adherence_pct": 83.3
}
```

---

### 9. Consultations

#### `POST /api/v1/consultations/start`
Start a new consultation (creates a Visit record).

**Request:**
```json
{
  "patient_id": "PT-1001",
  "doctor_id": "DR-201",
  "transcript": "Patient complains of chest pain..."
}
```

**Response:** `{ "visitId": 12, "patient_id": "PT-1001", "doctor_id": "DR-201" }`

---

#### `POST /api/v1/consultations`
Create or update a consultation with notes/summary. Optionally upload transcript to S3.

**Request:**
```json
{
  "patient_id": "PT-1001",
  "visit_id": 12,
  "notes": "BP elevated, started new medication",
  "summary": "Hypertension management visit",
  "transcript": "Doctor: How are you feeling?..."
}
```

---

#### `GET /api/v1/consultations/:visitId`
Retrieve a single visit with AI-generated summary and extracted medical entities.

**Response:**
```json
{
  "id": 12,
  "patient_id": "PT-1001",
  "patient": "Arjun Sharma",
  "doctor_id": "DR-201",
  "visit_date": "2026-03-05",
  "notes": "...",
  "summary": "...",
  "extracted_entities": { "medications": ["Metformin"], "conditions": ["hypertension"] },
  "created_at": "2026-03-05T06:00:00Z"
}
```

---

#### `POST /api/v1/consultations/:visitId/generate-summary`
Trigger Bedrock to generate a clinical summary and extract medical entities from the visit transcript/notes. Stored back to the Visit record.

**Request:** No body required.

**Response:**
```json
{
  "visitId": 12,
  "summary": "Patient presented with chest pain...",
  "extracted_entities": { "medications": ["Amlodipine"], "conditions": ["hypertension"] },
  "message": "Summary and entities generated."
}
```

---

### 10. Triage

#### `POST /api/v1/triage`
CDSS severity assessment (not a separate Triage agent). Routes to Bedrock AgentCore when `USE_AGENTCORE=true`, otherwise returns a structured stub. Aligns with Telemedicine MCP (Specialist escalation) in architecture.

**Request:**
```json
{
  "patient_id": "PT-1001",
  "doctor_id": "DR-201",
  "chief_complaint": "Severe chest pain radiating to left arm"
}
```

**Response:**
```json
{
  "patient_id": "PT-1001",
  "priority": "high",
  "confidence": 0.92,
  "risk_factors": ["potential cardiac event", "age > 50"],
  "recommendations": ["Immediate ECG", "Troponin test", "Cardiology consult"],
  "requires_senior_review": true,
  "safety_disclaimer": "Triage output is decision support only..."
}
```

---

### 11. Hospitals

#### `POST /api/v1/hospitals`  *(also accepts GET)*
Find nearest available hospitals for patient referral.

**Request:**
```json
{ "severity": "high", "limit": 5 }
```

**Response:**
```json
{
  "hospitals": [
    { "id": "H1", "name": "AIIMS Delhi", "distance_km": 3, "available": true }
  ],
  "safety_disclaimer": "Hospital availability is indicative..."
}
```

---

### 12. Admin Endpoints *(Admin role only)*

#### `GET /api/v1/admin/audit`
List recent audit log entries from Aurora.

**Query params:** `?limit=100` (max 500)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "user_id": "cognito-sub-uuid",
      "user_email": "doctor@hospital.in",
      "action": "GET /api/v1/patients",
      "resource": "/api/v1/patients",
      "timestamp": "2026-03-05T06:00:00Z"
    }
  ]
}
```

---

#### `GET /api/v1/admin/audit/export`
Download full audit log as CSV (DISHA compliance). Supports date range filtering.

**Query params:** `?from=2026-01-01&to=2026-03-31`

**Response:** `Content-Type: text/csv` — file download

---

#### `GET /api/v1/admin/users`
List Cognito users (when `COGNITO_USER_POOL_ID` is set).

**Response:**
```json
{
  "users": [
    { "id": "sub-uuid", "username": "dr.patel", "name": "Dr. Patel", "email": "...", "role": "doctor", "status": "active" }
  ]
}
```

---

#### `GET /api/v1/admin/config`
Retrieve system configuration from SSM Parameter Store (`/cdss/admin/config`).

**Response:** `{ "mcpHospitalEndpoint": "...", "featureFlags": { "aiAssist": true } }`

---

### 13. Doctor Activity

#### `POST /api/v1/activity`
Record a doctor-linked activity event for "My Activity" and compliance audit.

**Request:**
```json
{
  "doctor_id": "DR-201",
  "action": "view_patient",
  "patient_id": "PT-1001",
  "resource": "/patient/PT-1001",
  "detail": "Opened patient summary from dashboard"
}
```

**Response:**
```json
{
  "ok": true,
  "doctor_id": "DR-201",
  "patient_id": "PT-1001",
  "action": "view_patient",
  "resource": "/patient/PT-1001"
}
```

> Notes:
> - Writes into the existing `audit_log` table (`details` column) and CloudWatch logs.
> - Best-effort only: failures are logged but do not surface to the doctor UI.

#### `PUT /api/v1/admin/config`
Update system configuration (merges with existing SSM value).

**Request:** `{ "featureFlags": { "voiceInput": true } }`

---

#### `GET /api/v1/admin/analytics`
OT utilisation, conflict detection, and reminder statistics from Aurora.

**Response:**
```json
{
  "otUtilization": [{ "ot": "OT-1", "percent": 62 }],
  "otConflicts": [{ "ot": "OT-1", "date": "2026-03-10", "time": "09:00", "message": "OT-1 double-booked..." }],
  "reminderStats": { "sent": 25, "acknowledged": 25, "overdue": 5 },
  "agentUsage": []
}
```

---

#### `GET /api/v1/admin/compliance`
DISHA compliance dashboard: consent rates, retention status, and a 0–100 compliance score.

**Response:**
```json
{
  "total_audit_entries": 1500,
  "audit_entries_today": 42,
  "total_patients": 200,
  "patients_with_consent": 180,
  "consent_rate_percent": 90.0,
  "data_retention_status": "compliant",
  "oldest_record_age_days": 120,
  "retention_policy_days": 2555,
  "compliance_score": 87.5,
  "checked_at": "2026-03-05T06:00:00Z"
}
```

---

## Error Format

All errors follow the same structure:

```json
{ "error": "Patient not found" }
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (missing required fields) |
| `403` | Forbidden (wrong role or wrong patient ID) |
| `404` | Resource not found |
| `405` | Method not allowed |
| `409` | Conflict (e.g. slot already booked) |
| `500` | Internal server error |
| `503` | SNS/service not configured |

---

## Infrastructure Summary

| Component | AWS Service | Name |
|-----------|-------------|------|
| Compute | Lambda | `cdss-dev-router` |
| API | API Gateway | `cdss-api` |
| Auth | Cognito | `cdss-dev-user-pool` |
| Database | Aurora PostgreSQL | `cdss-dev-cluster` |
| AI | Bedrock (Claude 3.x) | via Secrets Manager config |
| Translation | Amazon Translate | `ap-south-1` |
| Language Detection | Amazon Comprehend | `ap-south-1` |
| Notifications | SNS | `cdss-dev-patient-reminders`, `cdss-dev-doctor-escalations` |
| Transcripts | S3 | `cdss-dev-transcripts-*` |
| CDN | CloudFront | for frontend static assets |
| Config | SSM Parameter Store | `/cdss/admin/config` |
| Secrets | Secrets Manager | `cdss-dev/rds-config`, `cdss-dev/bedrock-config`, `cdss-dev/app-config` (see [MCP_CONTRACTS.md](MCP_CONTRACTS.md)) |

### Key Environment Variables (Lambda)

| Variable | Purpose |
|----------|---------|
| `DATABASE_SECRET_NAME` | Points to Aurora credentials in Secrets Manager |
| `RDS_CONFIG_SECRET_NAME` | RDS/Aurora config (host, port, database, username) in Secrets Manager |
| `BEDROCK_CONFIG_SECRET_NAME` | Bedrock model ID + region in Secrets Manager |
| `CDSS_APP_CONFIG_SECRET_NAME` | App config: Cognito, MCP endpoints (`mcp_hospital_endpoint`, `mcp_abdm_endpoint`, `abdm_sandbox_url`), API base URL, optional MCP/ABDM API keys |
| `COGNITO_USER_POOL_ID` | For admin user listing |
| `SNS_TOPIC_PATIENT_REMINDERS_ARN` | Patient reminder notifications |
| `SNS_TOPIC_DOCTOR_ESCALATIONS_ARN` | Doctor escalation alerts |
| `USE_AGENTCORE` | `"true"` to enable Bedrock AgentCore runtime |
| `AGENT_RUNTIME_ARN` | AgentCore runtime ARN |
| `MCP_HOSPITAL_ENDPOINT` | (Optional) Hospital HIS MCP base URL — or set in app config secret |
| `MCP_ABDM_ENDPOINT` | (Optional) ABDM Gateway base URL — or set in app config secret |
| `ABDM_SANDBOX_URL` | (Optional) ABDM sandbox base URL for testing — or set in app config secret |
| `SUPPORTED_LANGUAGES` | Comma-separated codes: `en,hi,ta,te,bn` |
| `AWS_REGION` | `ap-south-1` |

**Secrets Manager (production):** All external URLs and credentials MUST come from Secrets Manager or IAM only. See [MCP_CONTRACTS.md](MCP_CONTRACTS.md) for MCP/ABDM secret keys. No hardcoded API keys or passwords in application code.

---

## Frontend Integration Checklist

- [ ] Set `Authorization: Bearer <cognito_id_token>` on every request
- [ ] Handle `403` → redirect to login / show permission error
- [ ] Handle `safety_disclaimer` field in AI responses — display prominently
- [ ] `/dashboard` → home screen stats
- [ ] `/api/v1/patients` → patient list page
- [ ] `/api/v1/patients/:id` → patient detail / consultation history
- [ ] `/api/v1/surgeries` + `/api/v1/surgeries/:id/analyse` → surgery management
- [ ] `/api/v1/resources` → OT / equipment / staff availability
- [ ] `/api/v1/schedule` → booking calendar
- [ ] `/api/v1/medications` + `/api/v1/reminders/nudge` → medication tracking
- [ ] `/api/v1/consultations/:id/generate-summary` → AI summary button
- [ ] `/agent` (POST) → AI chat interface (supervisor)
- [ ] `/api/v1/admin/compliance` + `/api/v1/admin/audit/export` → admin panel
