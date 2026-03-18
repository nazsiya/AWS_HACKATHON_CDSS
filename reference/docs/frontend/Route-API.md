# Routing API (POST /route) – frontend contract

**Endpoint:** `POST {BASE_URL}/route`  
**Auth:** Required. `Authorization: Bearer <Cognito Id Token>` (RMP).

---

## What it does

Returns **driving directions** between an origin and a destination: **distance_km**, **duration_minutes**, and **directions_url** (Google Maps link the user can open for turn-by-turn navigation).

**Backend flow:** API Gateway → **Route Lambda** → AgentCore **Gateway** (OAuth) → **maps-target___get_directions** → **gateway_maps Lambda** (Google Maps Routes API + builds directions_url). So the “routing” for this endpoint is done by the Route Lambda calling the Gateway maps tool; the **Routing AgentCore agent** is used when **POST /hospitals** is called with patient location (to add directions per hospital).

---

## Request

**Headers:** `Content-Type: application/json`, `Authorization: Bearer <IdToken>`

**Body:**

- **origin** – object with either:
  - **Coordinates:** `"lat"` (number, -90–90), `"lon"` (number, -180–180), or
  - **Address:** `"address"` (string, max 500 chars).
- **destination** – same as origin (lat/lon or address).

**Example (coordinates – e.g. from map picker or hospital lat/lon):**

```json
{
  "origin": { "lat": 12.97, "lon": 77.59 },
  "destination": { "lat": 12.8967, "lon": 77.5982 }
}
```

**Example (addresses – backend will geocode):**

```json
{
  "origin": { "address": "MG Road, Bangalore" },
  "destination": { "address": "Apollo Hospital, Bannerghatta Road, Bangalore" }
}
```

---

## Response (200)

| Field | Type | Notes |
|-------|------|--------|
| `distance_km` | number \| null | Driving distance in km. |
| `duration_minutes` | number \| null | Estimated driving time in minutes. |
| `directions_url` | string \| null | URL to open in Google Maps (web or app). |
| `stub` | boolean | Optional; true when Google Maps is not configured (then distance/duration/url may be null or placeholder). |

**Example response:**

```json
{
  "distance_km": 5.2,
  "duration_minutes": 12,
  "directions_url": "https://www.google.com/maps/dir/?api=1&origin=12.97,77.59&destination=12.8967,77.5982&travelmode=driving"
}
```

---

## Errors

| Status | Meaning |
|--------|--------|
| 400 | Invalid body (e.g. missing origin/destination, invalid lat/lon, address too long). Body has `error` and optional `detail`. |
| 401 | Missing or invalid token. |
| 500 | Server error (e.g. Gateway or maps Lambda failure). |
| 503 | Gateway not configured (gateway_config secret not populated; run setup_agentcore_gateway.py). |

---

## Frontend usage

1. Call when the user wants **directions** from current location (or selected address) to a **selected hospital** (use hospital’s lat/lon or address as destination).
2. Use **directions_url** as the “Open in Google Maps” link/button: `window.open(directions_url)` or open in the system maps app (e.g. `Intent.ACTION_VIEW` with the URL on Android).
3. Display **distance_km** and **duration_minutes** in the UI (e.g. “5.2 km, ~12 min”).
