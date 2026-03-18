# API integration guide – mobile app & web app

**Audience:** Mobile (Android/iOS) and web frontend teams, hackathon evaluators.  
**Purpose:** How to call the backend APIs: **RMP auth**, **triage → hospitals → route** pipeline, **real directions** (POST /route), and **Eka triage** (Indian medications and treatment protocols in recommendations).

---

## Base URL and auth

| Item | Value |
|------|--------|
| **Base URL** | From **Secrets Manager** after Terraform apply: run `eval $(python3 scripts/load_api_config.py --exports)` from project root – sets `API_URL`. Or: `cd infrastructure && terraform output -raw api_gateway_url` (e.g. `https://xxxx.execute-api.us-east-1.amazonaws.com/dev/`). |
| **Auth** | All POST endpoints except health require **Cognito Id Token**. Send header: `Authorization: Bearer <IdToken>`. |
| **Sign-in** | Use [RMP-AUTH.md](./RMP-AUTH.md) for Amplify / Cognito setup. Backend provides **User Pool ID** and **Client ID** (from Terraform). |

Without a valid token, **POST /triage**, **POST /hospitals**, and **POST /route** return **401 Unauthorized**.

---

## Endpoints overview

| Endpoint | Method | Auth | Use |
|----------|--------|------|-----|
| **/health** | GET | No | Liveness check; no body. |
| **/triage** | POST | Yes | Submit symptoms/vitals; get severity, recommendations, `session_id`. |
| **/hospitals** | POST | Yes | Get hospital recommendations for a severity; optional patient location for distance. |
| **/route** | POST | Yes | Get **real driving directions** between origin and destination (distance, duration, Google Maps URL). |

---

## 1. GET /health

- **URL:** `{BASE_URL}/health`
- **Headers:** None required.
- **Response:** `200` with simple body (e.g. `{"status":"ok"}`). Use to verify API is up before calling protected endpoints.

---

## 2. POST /triage

- **URL:** `{BASE_URL}/triage`
- **Headers:** `Content-Type: application/json`, `Authorization: Bearer <IdToken>`
- **Body:** See [triage-api-contract.md](./triage-api-contract.md). Minimum: `symptoms` (array of strings). Optional: `vitals`, `age_years`, `sex`, `session_id`, `patient_id`.
- **Response:** `200` with `severity`, `confidence`, `recommendations`, `force_high_priority`, `safety_disclaimer`, **`session_id`** (reuse for /hospitals and /route), `id` (when persisted).

**Eka (Indian drugs & protocols):** When the user’s symptoms or free text ask for **Indian drug brands** (e.g. “patient wants Indian paracetamol brands”) or **treatment protocols** (e.g. “fever protocol”, “ORS and dehydration protocol”), the triage AI may call Eka Care via the Gateway. In that case **recommendations** can include specific Indian brand names (e.g. Modi Lifecare, Lyka Labs, Alkem) and/or protocol-style steps (e.g. WHO dehydration classification, zinc supplementation). Frontend can display `recommendations` as-is; no extra fields.

**Example request (mobile/web):**

```json
{
  "symptoms": ["chest pain", "shortness of breath"],
  "vitals": { "heart_rate": 110, "blood_pressure_systolic": 140 },
  "age_years": 55,
  "sex": "M",
  "session_id": "optional-uuid-at-least-33-chars"
}
```

---

## 3. POST /hospitals

- **URL:** `{BASE_URL}/hospitals`
- **Headers:** `Content-Type: application/json`, `Authorization: Bearer <IdToken>`
- **Body:**
  - **Required:** `severity` (from triage: `"critical"` \| `"high"` \| `"medium"` \| `"low"`), `recommendations` (array, from triage).
  - **Optional:** `limit` (default 3), `session_id` (same as triage for memory), `patient_location_lat`, `patient_location_lon` (for distance/directions from patient to hospital).

- **Response:** `200` with `hospitals` array (name, match_score, match_reasons, lat, lon, etc.) and `safety_disclaimer`.

**Example request:**

```json
{
  "severity": "high",
  "recommendations": ["Emergency department"],
  "limit": 3,
  "session_id": "same-uuid-as-triage",
  "patient_location_lat": 12.97,
  "patient_location_lon": 77.59
}
```

---

## 4. POST /route (real directions)

- **URL:** `{BASE_URL}/route`
- **Headers:** `Content-Type: application/json`, `Authorization: Bearer <IdToken>`
- **Body:**
  - **Origin and destination** – either coordinates or address:
    - **Coordinates:** `"origin": { "lat": 12.97, "lon": 77.59 }`, `"destination": { "lat": 13.08, "lon": 80.27 }`
    - **Addresses:** `"origin": { "address": "MG Road, Bangalore" }`, `"destination": { "address": "Chennai Central, Chennai" }` (requires Geocoding; backend uses same API key)

- **Response:** `200` with:
  - **`distance_km`** – driving distance in km (real, from Google Routes API).
  - **`duration_minutes`** – estimated driving time in minutes.
  - **`directions_url`** – deep link to open in **Google Maps** (web or mobile). Use this so the user can navigate.

**Example request (coordinates – typical from map picker or hospital lat/lon):**

```json
{
  "origin": { "lat": 12.97, "lon": 77.59 },
  "destination": { "lat": 13.08, "lon": 80.27 }
}
```

**Example request (addresses):**

```json
{
  "origin": { "address": "MG Road, Bangalore" },
  "destination": { "address": "Apollo Hospital, Chennai" }
}
```

**Example response:**

```json
{
  "distance_km": 325.08,
  "duration_minutes": 413,
  "directions_url": "https://www.google.com/maps/dir/?api=1&origin=12.97,77.59&destination=13.08,80.27&travelmode=driving"
}
```

**Mobile:** Open `directions_url` in the system browser or in-app WebView / Google Maps app (e.g. `Intent.ACTION_VIEW` with the URL on Android).  
**Web:** Use `window.open(directions_url)` or an `<a href="..." target="_blank">Open in Google Maps</a>`.

---

## Recommended flow (mobile & web)

1. **Sign in** (Cognito) → get **Id Token**. See [RMP-AUTH.md](./RMP-AUTH.md).
2. **Optional:** Generate a **session_id** (UUID, ≥33 chars) at flow start; reuse for triage, hospitals, route.
3. **POST /triage** with symptoms/vitals → get `severity`, `recommendations`, `session_id`.
4. **POST /hospitals** with `severity`, `recommendations`, optional `patient_location_lat/lon` and `session_id` → get list of hospitals.
5. When the user selects a hospital (or wants directions from current location to a hospital), call **POST /route** with:
   - `origin`: current location (lat/lon from device or address) or patient address.
   - `destination`: selected hospital’s lat/lon or address.
6. Show **distance_km** and **duration_minutes** in the UI and provide a button/link using **directions_url** to open Google Maps.

---

## Error handling

| Status | Meaning |
|--------|---------|
| **401** | Missing or invalid token. Refresh token or re-prompt sign-in. |
| **400** | Bad request (e.g. missing `origin`/`destination`, invalid body). Response body has `error` and optional `detail`. |
| **500** | Server error. Response body may include `error` and `detail`. |

Always send `Authorization: Bearer <IdToken>` for POST /triage, /hospitals, /route. Handle 401 by refreshing the Id Token or redirecting to sign-in.

---

## References

| Doc | Purpose |
|-----|--------|
| [RMP-AUTH.md](./RMP-AUTH.md) | Cognito sign-in, Amplify/Cognito SDK, getting Id Token |
| [triage-api-contract.md](./triage-api-contract.md) | Full triage request/response, session_id, Eka behavior, mobile mapping |
| [Hospital-Matcher-API.md](./Hospital-Matcher-API.md) | **POST /hospitals** contract – request/response, patient location, directions_url per hospital |
| [Route-API.md](./Route-API.md) | **POST /route** contract – origin/destination, distance_km, duration_minutes, directions_url |
| [openapi.yaml](../openapi.yaml) | **Full Swagger/OpenAPI 3.0** – all endpoints, schemas, auth; use for codegen or Swagger UI |
| [TESTING-Pipeline-curl.md](../backend/TESTING-Pipeline-curl.md) | Curl examples for the full pipeline (backend/testing) |
| [TESTING-Gateway-Eka.md](../backend/TESTING-Gateway-Eka.md) | Eka triage test cases (medications, protocols) for demo/QA |
