# Hospital Matcher API (frontend contract)

**Endpoint:** `POST {BASE_URL}/hospitals`  
**Auth:** Required. `Authorization: Bearer <Cognito Id Token>` (RMP).

---

## What it does

Returns a list of **hospital recommendations** for a given triage result (severity + recommendations). When the client sends **patient location** (lat/lon), the backend can include **distance_km**, **duration_minutes**, and **directions_url** (Google Maps link) per hospital.

**Backend flow:** API Gateway → Hospital Matcher Lambda → **Hospital Matcher AgentCore runtime** → Gateway **get_hospitals** tool (real Bangalore/Chennai seed data when configured) and optionally **get_route** (Routing agent → maps) for directions. So the “agent” is the Hospital Matcher runtime; MCPs are get_hospitals and get_route via the Gateway.

---

## Request

**Headers:** `Content-Type: application/json`, `Authorization: Bearer <IdToken>`

**Body:**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `severity` | string | **Yes** | One of: `"critical"`, `"high"`, `"medium"`, `"low"`. Should come from POST /triage response. |
| `recommendations` | string[] | **Yes** | Array of strings from triage (e.g. `["Emergency department"]`). Can be empty array. |
| `limit` | number | No | Number of hospitals to return (1–10). Default 3. |
| `session_id` | string | No | Same as triage for memory continuity (≥33 chars, e.g. UUID). |
| `patient_id` | string | No | Optional patient identifier. |
| `triage_assessment_id` | string | No | Optional DB assessment id. |
| `patient_location_lat` | number | No | Patient latitude (-90–90). When set with `patient_location_lon`, backend may return `distance_km`, `duration_minutes`, `directions_url` per hospital. |
| `patient_location_lon` | number | No | Patient longitude (-180–180). |

**Example (no location):**

```json
{
  "severity": "high",
  "recommendations": ["Emergency department"],
  "limit": 3
}
```

**Example (with location for directions):**

```json
{
  "severity": "high",
  "recommendations": ["Emergency department"],
  "limit": 3,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "patient_location_lat": 12.97,
  "patient_location_lon": 77.59
}
```

---

## Response (200)

| Field | Type | Notes |
|-------|------|--------|
| `hospitals` | array | List of hospital objects (see below). |
| `safety_disclaimer` | string \| null | e.g. "Hospital availability may change. Confirm with facility before transport." |

**Hospital object:**

| Field | Type | Notes |
|-------|------|--------|
| `hospital_id` | string | e.g. `blr-apollo-1`, `stub-1`. |
| `name` | string | Hospital name. |
| `match_score` | number | 0–1. |
| `match_reasons` | string[] | e.g. `["24/7 Emergency", "City: Bangalore"]`. |
| `estimated_minutes` | number \| null | Travel time in minutes when patient location was sent; null otherwise. |
| `specialties` | string[] | Optional. |
| `distance_km` | number \| null | Driving distance when patient location was sent. |
| `duration_minutes` | number \| null | Driving duration in minutes. |
| `directions_url` | string \| null | Google Maps URL to open for directions (when patient location was sent and routing is configured). |

**Example response:**

```json
{
  "hospitals": [
    {
      "hospital_id": "blr-apollo-1",
      "name": "Apollo Hospital, Bannerghatta Road",
      "match_score": 0.9,
      "match_reasons": ["24/7 Emergency", "City: Bangalore"],
      "estimated_minutes": 12,
      "specialties": [],
      "distance_km": 5.2,
      "duration_minutes": 12,
      "directions_url": "https://www.google.com/maps/dir/?api=1&origin=12.97,77.59&destination=12.8967,77.5982&travelmode=driving"
    }
  ],
  "safety_disclaimer": "Hospital availability may change. Confirm with facility before transport."
}
```

---

## Errors

| Status | Meaning |
|--------|--------|
| 400 | Invalid body (e.g. invalid severity, limit out of range, lat/lon out of bounds). Body has `error` and optional `detail`. |
| 401 | Missing or invalid token. |
| 500 | Server error. |
| 504 | Gateway timeout (e.g. when requesting many hospitals with patient location; try lower `limit`). |

---

## Frontend usage

1. Call after **POST /triage**; use `severity` and `recommendations` from the triage response.
2. Send the same **session_id** as triage if you have one.
3. If the user has **current location**, send **patient_location_lat** and **patient_location_lon** to get **directions_url** per hospital.
4. Show **directions_url** as a button/link “Open in Google Maps” (e.g. `window.open(directions_url)` or `Intent.ACTION_VIEW` on Android).
