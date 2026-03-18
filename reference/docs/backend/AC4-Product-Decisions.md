# AC-4: Product decisions (Feb 2026)

**Purpose:** Record decisions and open items for AC-4 (Routing + Identity, multi-agent, Google Maps, guardrails). See [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) for technical design.

---

## 1. Hospitals + routes: combined response (Option A)

**Decision:** **Option A – Combined response.**

- Frontend calls **POST /hospitals** once with triage result + optional patient location (lat/lon or address).
- Response includes **hospitals and per-hospital route info** (distance, ETA, directions link) when patient location is provided.
- POST /route remains for “route only” (e.g. user already selected a hospital).

---

## 2. Google Maps: use now – cost summary

**Decision:** **Use Google Maps now** (Directions + Geocoding for address support).

### Cost (approximate)

Google Maps Platform is **pay-per-use**. Billing is per “billable event” (e.g. one route request = one event).

| API | What we use it for | Free tier (monthly) | After free tier (per 1,000 events) |
|-----|--------------------|----------------------|-------------------------------------|
| **Directions** (or Routes: Compute Routes) | One route from A → B | **10,000** free (global) / **70,000** free (India) | Global: ~$5; **India: ~$1.50** |
| **Distance Matrix** (or Route Matrix) | One request: 1 origin × N hospitals (distance/ETA for all) | Same as above | Same |
| **Geocoding** | Convert address text → lat/lon | **10,000** free (global) / **70,000** free (India) | Global: ~$5; **India: ~$1.50** |

**India-specific (Bangalore/Chennai):**  
[India pricing](https://developers.google.com/maps/billing-and-pricing/pricing-india) has **higher free caps** (e.g. 70,000 free for Routes and Geocoding in India). If your Google Cloud billing is set to India, you get the India SKUs and free tier.

**Rough cost per “session” (one user: triage → hospitals with routes):**

- 1 Geocode (if user sends address): 1 event.
- 1 Route Matrix (1 origin × 3 hospitals): 3 elements = 3 events (or 3× Directions = 3 events).
- **Total ~4 events per session** for routing + geocode.

**Example monthly cost:**

- **Under 70k sessions/month (India):** Routing + Geocoding can stay within **free tier** → **$0**.
- **Above free tier (India):** ~₹0.12–0.15 per session (at ~$1.50/1000 events).
- **Global (if not India):** ~$5/1000 → ~$0.02 per session above 10k free.

**You need:** A Google Cloud project with **Maps Platform** enabled and **billing** attached. No upfront cost; set a budget alert (e.g. $50/month) to avoid surprises.

---

## 3. RMP auth (Identity) – explained

**Your answer:** Not sure – need more explanation.

### What “RMP auth” means here

- **RMP** = Registered Medical Practitioner (doctor/nurse/paramedic using the app).
- **Auth** = Proving who is calling the API (e.g. “this request is from Dr. X”) so we can:
  - **Audit:** “Who ordered this triage?” (e.g. for compliance).
  - **Access control:** Restrict sensitive actions (e.g. view history) to logged-in RMPs.
  - **Personalization:** Optionally show “logged in as Dr. X” in the UI.

### How it would work (when we implement it)

1. **Frontend:** RMP logs in (e.g. username/password or hospital SSO) and gets a **token** (JWT or session id).
2. **Backend:** For protected endpoints (e.g. POST /triage, /hospitals, /route), the API checks the token:
   - If **valid** → allow request and optionally pass “user id” or “rmp_id” to AgentCore / DB (for audit).
   - If **missing or invalid** → 401 Unauthorized (or allow anonymous with “anonymous” in audit).
3. **Where identity lives:** Usually **Amazon Cognito** (user pool) or another **IdP** (Identity Provider) that issues the token. AgentCore’s “Identity” feature can plug into that so the runtime knows “this run is for user X.”

### Options for you

| Option | Meaning |
|--------|--------|
| **Defer** | Don’t implement auth in AC-4. All API calls are “anonymous.” We **document** the intended design (Cognito/IdP, which endpoints to protect) and implement later when frontend has login. |
| **Implement in AC-4** | Add Cognito (or your IdP), protect chosen endpoints, pass identity to backend/AgentCore. Requires: who are the users (e.g. one Cognito user pool), and how will frontend get the token (e.g. Amplify Auth, or custom login). |

**Recommendation:** **Defer** RMP auth to a later phase unless you already have an IdP and want “only logged-in RMPs can use the app” for the hackathon. We’ll keep “Identity (Cognito/IdP) for RMP” in the design as a documented deliverable for when you’re ready.

---

## 4. Route input: full support (user-friendly)

**Decision:** **Support both coordinates and addresses.**

- **Coordinates:** `origin: { "lat": 12.97, "lon": 77.59 }`, `destination: { "lat", "lon" }` or `hospital_id`.
- **Addresses:** `origin: { "address": "MG Road, Bangalore" }` (or similar). Backend uses **Geocoding** to convert address → lat/lon, then calls Directions/Matrix.
- **Validation:** Standard coordinate bounds (lat -90–90, lon -180–180); one origin, one destination per request; reasonable string length for address.

---

## 5. Hospital data: add from internet (Bangalore / Chennai)

**Decision:** **Add real hospital data from the internet; for now Bangalore and Chennai.**

- **Source:** Use a defined source (e.g. **Google Places API** “hospital” search, or **OpenStreetMap**/Overpass, or a curated list) to fetch hospitals with name, address, and lat/lon.
- **Scope:** Bangalore and Chennai only for now. Store in the same shape as current hospital data (id, name, address, lat, lon, match_score, etc.) so Hospital Matcher and Routing can use it.
- **Implementation:** Either (a) seed DB/S3/JSON with a one-time script that calls Places/OSM and writes records, or (b) Gateway get_hospitals Lambda (or a new data layer) fetches from Places/OSM and caches. Design doc to specify “hospital data: Bangalore + Chennai from [chosen source].”

---

## 6. Route guardrails

**Decision:** **Standard coordinate validation + one origin / one destination only.**

- No extra business rules (e.g. max radius, region restrictions) for AC-4.
- Validate: lat/lon in range; optional hospital_id format; max one origin, one destination per POST /route.

---

## Summary table

| # | Topic | Decision |
|---|--------|----------|
| 1 | Hospitals + routes | **Option A** – combined response from POST /hospitals |
| 2 | Google Maps | **Use now** – see cost summary above; India has higher free tier |
| 3 | RMP auth | **Defer** – document design; implement when frontend has login / IdP |
| 4 | Route input | **Full support** – coordinates + address (Geocoding) |
| 5 | Hospital data | **Add from internet** – Bangalore + Chennai for now |
| 6 | Route guardrails | **Standard** – coordinate validation, one origin/destination |

---

## References

- [AC4-Routing-Identity-Design.md](./AC4-Routing-Identity-Design.md) – Technical design
- [Google Maps Platform pricing (global)](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Google Maps Platform pricing (India)](https://developers.google.com/maps/billing-and-pricing/pricing-india)
