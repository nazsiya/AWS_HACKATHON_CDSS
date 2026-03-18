# Triage API Contract (Backend ↔ Mobile)

**Real API base URL:** `https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev`  
**Triage endpoint:** `POST https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev/triage`

This doc matches the backend implementation and what the mobile app must send/receive.

---

## How the backend works

1. **API Gateway** forwards `POST /triage` to the **Triage Lambda**.
2. **Lambda** (`src/triage/api/handler.py`) parses JSON body into `TriageRequest`, calls `assess_triage(request)`.
3. **Core** (`src/triage/core/agent.py`) uses Bedrock (AgentCore or Converse API) with tools; if **Eka** is enabled (Gateway env vars on triage runtime), the model can call `search_indian_medications` and `search_treatment_protocols`. Recommendations may then include **Indian drug brands** and **treatment protocol** steps (e.g. ICMR-style).
4. **Response** is validated with `TriageResult` Pydantic model and returned as JSON.

---

## Request (what the mobile app must send)

**Method:** `POST`  
**Headers:** `Content-Type: application/json`  
**Body:** JSON matching backend `TriageRequest`:

| Field        | Type           | Required | Notes |
|-------------|----------------|----------|--------|
| `symptoms`  | `string[]`     | **Yes**  | At least one symptom (e.g. `["chest pain", "shortness of breath"]`). Can come from app’s symptom step (e.g. `primarySymptoms` + `freeText` split into list). |
| `vitals`    | `object`       | No       | Key-value map of vital names to numbers. Backend accepts any `dict[str, float]`. Use same keys the AI expects, e.g. `bp` (systolic), `heart_rate`, `spo2`, `temp_c`, `respiratory_rate`, etc. |
| `age_years` | `number` (int) | No       | 0–150. Map from app’s `PatientInfo.age`. |
| `sex`       | `string`       | No       | Map from app’s `PatientInfo.gender`. |
| `submitted_by` | `string`    | No       | RMP or user identifier. |
| `session_id`   | `string`    | No       | **AC-3:** Reuse same AgentCore session across triage → hospitals → route. Must be **≥ 33 characters** (e.g. UUID). If omitted or shorter, backend generates a UUID and returns it — use that for subsequent calls. |
| `patient_id`    | `string`    | No       | Optional patient identifier for long-term memory. |

**Example (matches your curl):**

```json
{
  "symptoms": ["chest pain", "shortness of breath"],
  "vitals": { "bp": 180, "heart_rate": 95 }
}
```

**Example with optional fields:**

```json
{
  "symptoms": ["fever", "cough"],
  "vitals": { "bp": 120, "heart_rate": 88, "spo2": 97, "temp_c": 38.5 },
  "age_years": 45,
  "sex": "M"
}
```

**Mobile → API mapping (when you wire real client):**

- **symptoms:** Build from `SymptomInput`: e.g. `primarySymptoms` + split `freeText` by comma/newline into a single list; ensure at least one string.
- **vitals:** From `VitalsInput` → e.g. `heart_rate` ← `heartRateBpm`, `bp` ← `bloodPressureSystolic` (or send both sys/dia if backend adds support), `spo2` ← `spo2Percent`, `temp_c` ← `temperatureCelsius`, `respiratory_rate` ← `respiratoryRatePerMin`.
- **age_years:** `PatientInfo.age`.
- **sex:** `PatientInfo.gender`.

---

## Response (what the mobile app receives)

**Success:** `200` with JSON body matching backend `TriageResult`:

| Field                 | Type      | Notes |
|-----------------------|-----------|--------|
| `severity`            | `string`  | One of: `"critical"`, `"high"`, `"medium"`, `"low"`. |
| `confidence`          | `number`  | 0.0–1.0 (e.g. 0.82). |
| `recommendations`     | `string[]`| List of action items. |
| `force_high_priority` | `boolean` | `true` when confidence < 85%; treat as high priority. |
| `safety_disclaimer`   | `string \| null` | Single disclaimer text. |
| `session_id`         | `string \| null` | **AC-3:** Session ID used for this request (echoed or backend-generated). **Store this and send it with POST /hospitals and POST /route** so the backend reuses the same AgentCore session (memory continuity). |
| `id`                 | `string` (UUID) | Present when triage was persisted to DB; use for audit or follow-up. |

**Example (from your curl):**

```json
{
  "severity": "high",
  "confidence": 0.82,
  "recommendations": ["Activate emergency transport immediately — do not delay", "..."],
  "force_high_priority": true,
  "safety_disclaimer": "This is AI-assisted guidance. Seek professional medical care."
}
```

**Mobile model mapping (current app vs API):**

| Backend (API)           | Mobile (TriageResult in TriageModels.kt)     |
|-------------------------|----------------------------------------------|
| `severity`              | `SeverityLevel` (map string → enum)          |
| `confidence`            | `confidencePercent` (× 100, e.g. 0.82 → 82)  |
| `recommendations`       | `recommendedActions`                         |
| `force_high_priority`   | `flaggedForReview`                           |
| `safety_disclaimer`     | `safetyDisclaimers` (single item in list) or one string |
| *(not in API)*          | `emergencyId` (generate client-side or add to backend later) |

---

## Summary

- **Base URL:** `https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev`
- **Endpoint:** `POST /triage` → full URL: `https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev/triage`
- **Input:** `symptoms` (required, ≥1), `vitals` (optional dict), optional `age_years`, `sex`.
- **Output:** `severity`, `confidence`, `recommendations`, `force_high_priority`, `safety_disclaimer`.
- **Eka:** When the user asks for Indian brands or treatment protocols (e.g. in symptoms or free text), `recommendations` may include Indian drug names (e.g. Modi Lifecare, Lyka Labs) and/or protocol-style steps (e.g. ORS, WHO dehydration). Display as-is.
- When integrating the real API in the app, map `SymptomInput`/`VitalsInput`/`PatientInfo` → request JSON, and response JSON → `TriageResult` (with `emergencyId` generated or from a future backend field).

---

## POST /route (real directions)

After triage and hospital selection, use **POST /route** to get **real driving directions** (distance, duration, Google Maps URL). Full request/response and flow are documented in [API-Integration-Guide.md](./API-Integration-Guide.md).

- **URL:** `{BASE_URL}/route`
- **Auth:** Same as triage/hospitals: `Authorization: Bearer <IdToken>`.
- **Body:** `origin` and `destination`, each either `{ "lat", "lon" }` or `{ "address": "..." }`.
- **Response:** `distance_km`, `duration_minutes`, `directions_url` (open in Google Maps on mobile or web).

---

## Tracking session_id from the frontend (AC-3)

To keep **one AgentCore session** (and short-term memory) across **triage → hospital match → route**, the frontend must send the same `session_id` on each API call. Backend requires `session_id` to be **at least 33 characters** (e.g. a UUID).

### Option A: Frontend generates UUID at flow start (recommended)

1. When the user starts a new case (e.g. "New assessment" or after opening the triage form), generate a UUID in the frontend:
   - **Web:** `crypto.randomUUID()` (or `uuid` lib).
   - **Android:** `UUID.randomUUID().toString()`.
   - **iOS:** `UUID().uuidString`.
2. Store it for the duration of the flow:
   - **In-memory:** React state, Vue ref, or a “flow”/“case” context that holds `sessionId`, triage result, selected hospital, etc.
   - **Optional:** `sessionStorage.setItem('triageSessionId', sessionId)` so it survives refresh in the same tab; clear when the flow ends or on logout.
3. Send it on every call:
   - **POST /triage** body: `{ "symptoms": [...], "session_id": "<your-uuid>" }`.
   - **POST /hospitals** body: `{ "severity": "...", "recommendations": [...], "session_id": "<same-uuid>" }`.
   - **POST /route** (when AC-4 exists): same `session_id`.

### Option B: Use the session_id returned by triage

1. First **POST /triage** without `session_id` (or with a short id). Backend returns `session_id` in the response (a UUID).
2. Store that value (state or sessionStorage) and send it on **POST /hospitals** and **POST /route**.

### Where to store

| Place | Use when |
|-------|----------|
| **Component/context state** | One “flow” object (e.g. `{ sessionId, triageResult, hospitalMatch }`) for the current case. Cleared when user leaves the flow or starts a new case. |
| **sessionStorage** | Same as above, but survives page refresh in the same tab. Key e.g. `triageSessionId` or `currentCaseSessionId`. Clear on flow end. |
| **localStorage** | Only if you need to correlate across browser sessions (e.g. “resume case” next day); otherwise prefer sessionStorage or in-memory. |

Do **not** put the session UUID in the URL (it would leak in history/logs). Prefer state or sessionStorage.

### Example (pseudo-code)

```javascript
// Start of flow (e.g. "New assessment" or triage screen mount)
const sessionId = crypto.randomUUID();  // 36 chars, valid
setFlowState(prev => ({ ...prev, sessionId }));

// POST /triage
const triageRes = await fetch(`${API_URL}/triage`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ symptoms, vitals, age_years, sex, session_id: sessionId }),
});
const triage = await triageRes.json();
// triage.session_id will equal sessionId (or backend UUID if you had sent a short one)

// POST /hospitals (reuse same sessionId)
const hospitalsRes = await fetch(`${API_URL}/hospitals`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    severity: triage.severity,
    recommendations: triage.recommendations,
    session_id: sessionId,
  }),
});
```
