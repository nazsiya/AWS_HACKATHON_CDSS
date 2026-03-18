# Emergency Medical Triage — Android Mobile App Plan

**Scope:** Android mobile app frontend only. No changes to web app, backend, infra, or voice.

**You work in:** A new Android project (e.g. `emergency-medical-triage/frontend/mobile-android/`).  
**You do not touch:** `emergency-medical-triage/frontend/web/` (web app), `emergency-medical-triage/src/`, `emergency-medical-triage/infrastructure/`, voice interface.

---

## 1. Tech Stack (Android)

| Layer | Choice | Notes |
|-------|--------|--------|
| **Language** | Kotlin | Standard for Android |
| **UI** | Jetpack Compose + Material 3 | Declarative, single toolkit |
| **Navigation** | Compose Navigation | Single-activity, type-safe routes |
| **Networking** | Retrofit + OkHttp (or Ktor Client) | One API client → API Gateway only (minimal hop) |
| **Local storage** | DataStore (prefs) + Room (if offline cache beyond prefs) | Language, auth token, offline queue |
| **DI** | Hilt | Scoped to app/session |
| **Min SDK** | 24+ | Broad device support for rural/low-end devices |
| **Target SDK** | 34 | Current stable |

**Design / UX:** Medical-grade, calm, trustworthy. Use the same severity colors and patterns as in `frontend_workflow.md` (Critical/High/Medium/Low). Support **7 languages**: Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati (strings + optional in-app language selector).

**Guardrails that apply to the mobile app:**
- **Safety:** When AI confidence &lt; 85%, show as high priority and “Flag for doctor review”; always show safety disclaimers on triage results.
- **No secrets in app:** Auth via token (e.g. JWT from `/auth/login`); API base URL from build config / env, never hardcoded API keys or DB credentials.
- **Offline:** Cached triage for common scenarios + cached hospital data (e.g. 50 km); sync when back online (`/sync/upload`, `/sync/download`).

**Dashboards / roles (mobile app):**
- **1. User (Healthcare Worker):** Main flow — Triage tab, Hospitals tab, Dashboard tab, More. Role badge in top bar (e.g. “Healthcare Worker”).
- **2. RMP Dashboard:** The “Dashboard” tab is the RMP (Rural Medical Practitioner) view: profile, competency, learning modules, “Start Triage” / guidance.
- **3. Admin / Hospital Staff:** Planned for later (or web); not separate screens in the current mobile build.

---

## 2. API Endpoints the Mobile App Will Use

Same contract as in `frontend_workflow.md` §9. Backend team owns implementation; mobile only consumes.

**Real API base (current):** `https://vrxlwtzfff.execute-api.us-east-1.amazonaws.com/dev` — triage is **POST `/triage`** (see `docs/frontend/triage-api-contract.md`).

| Endpoint | Method | Use in app |
|----------|--------|------------|
| `/auth/login` | POST | Login → store JWT |
| `/auth/validate` | GET | Validate token & role |
| `/triage` | POST | Submit symptoms + vitals → severity (real endpoint; plan also references `/triage/assess`) |
| `/triage/report/{id}` | GET | Triage report screen |
| `/triage/override/{id}` | PUT | Override AI recommendation |
| `/hospitals/match` | POST | Top 3 hospital matches |
| `/hospitals/{id}/status` | GET | Hospital status |
| `/routing/calculate` | POST | Route to hospital |
| `/routing/navigate/{id}` | GET | Turn-by-turn steps |
| `/rmp/profile/{id}` | GET | RMP dashboard |
| `/rmp/guidance/{emergencyId}` | GET | Procedural guidance overlay |
| `/rmp/learning/modules` | GET | Learning screen |
| `/rmp/telemedicine/connect` | POST | Escalate to doctor |
| `/collective/insights/{region}` | GET | Regional insights |
| `/collective/share` | POST | Share anonymized case |
| `/language/translate` | POST | Translate symptom text |
| `/language/audio` | POST | Text-to-speech (accessibility) |
| `/sync/upload` | POST | Sync offline assessments |
| `/sync/download` | GET | Download cache (hospitals, scenarios) |

Until backend is ready, use **mock data** in the app (or a local mock server) with the same request/response shapes.

---

## 3. Step-by-Step Plan (What We’re Going to Do)

Aligned with `task.md` and `frontend_workflow.md`, adapted for **Android only**. RMP/Healthcare Worker is the primary mobile user; Admin/Hospital Staff portals can be web-only or added later on mobile.

---

### Phase 1 — Foundation (Design system & app shell)

1. **Create Android project** under `emergency-medical-triage/frontend/mobile-android/` (Kotlin, Compose, single activity, no web/Compose multiplatform unless you decide otherwise).
2. **Design system:**
   - Theme: light/dark (Material 3), severity colors (Critical / High / Medium / Low), typography (readable, medical).
   - Tokens: spacing (e.g. 4/8/16/24 dp), radii, optional elevation.
3. **App shell:**
   - Bottom navigation (e.g. Triage, Hospitals, Dashboard, More).
   - Top bar with role badge (e.g. “Healthcare Worker”).
   - Global offline banner (“OFFLINE MODE — LIMITED FUNCTIONALITY” + last sync time).
4. **No backend/infra changes.** Optional: add a `docs/README.md` in `frontend/mobile-android/` describing scope and “do not edit” list.

**Exit criteria:** App runs; shell + theme + offline banner visible; no edits outside `frontend/mobile-android/`.

---

### Phase 2 — Auth & language

1. **Login screen:** Email/phone + password; “Sign in” → call `/auth/login` (or mock), store JWT; optional biometric placeholder (icon/button).
2. **Session:** Validate with `/auth/validate` on app start; redirect to login if invalid.
3. **Language selector:** 7 languages (Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati); persist in DataStore; apply to UI strings (resource files or in-app mapping).
4. **Role-based entry:** After login, show main flow for Healthcare Worker / RMP; no need to implement Hospital Staff / Admin flows on mobile in this phase.

**Exit criteria:** Login (mock or real), language selection persisted, role shown in shell.

---

### Phase 3 — Core triage flow

1. **Triage wizard (4 steps):**
   - **Step 1 — Patient info:** Age, gender, location (GPS auto-detect), optional medical history, allergies.
   - **Step 2 — Symptoms:** Multi-select + free-text, duration, severity; optional voice input placeholder.
   - **Step 3 — Vitals:** Heart rate, BP, temp, SpO2, respiratory rate, consciousness (AVPU).
   - **Step 4 — Result:** Severity badge (Critical/High/Medium/Low), confidence (e.g. ring or %), recommended actions, **safety disclaimers**, override button; if confidence &lt; 85% → show as high priority + “Flag for doctor review”.
2. **API:** Call `/triage/assess` (or mock) from step 4; show loading then result.
3. **Triage report screen:** Structured view of result; “Proceed to Hospital Matching” CTA.
4. **Offline:** If offline, show cached triage (e.g. 20 common scenarios) + “OFFLINE MODE” banner; queue assessment for `/sync/upload` when online.

**Exit criteria:** Full 4-step wizard, result screen with guardrails, report screen, offline path.

---

### Phase 4 — Hospital matching & routing

1. **Hospital match screen:** After triage, call `/hospitals/match` (or mock); show **top 3** as cards (name, distance/ETA, beds, specialist status, match score); “Navigate” per card.
2. **Navigation screen:** Map placeholder or integrate maps (e.g. Google Maps Intent or SDK); floating panel: ETA, turn-by-turn (from `/routing/navigate/{id}` or mock); “Re-route” / “Change hospital”; “Generate Handoff Report” on arrival.
3. **Routing API:** Use `/routing/calculate` and `/routing/navigate/{id}` when backend is ready.

**Exit criteria:** Top 3 hospitals, navigation UI, handoff report entry point.

---

### Phase 5 — RMP dashboard & training (mobile RMP features)

1. **RMP dashboard:** Competency profile (e.g. from `/rmp/profile/{id}`), stats, quick actions, recent cases.
2. **Guidance overlay:** Step-by-step procedural guidance (e.g. from `/rmp/guidance/{emergencyId}`); slide-up or bottom sheet.
3. **Learning screen:** Micro-learning modules (e.g. from `/rmp/learning/modules`), progress, achievements; optional telemedicine escalation (`/rmp/telemedicine/connect`).

**Exit criteria:** Dashboard, guidance UI, learning list/detail.

---

### Phase 6 — Optional / later (Admin & hospital staff on mobile)

- **Admin dashboard / Hospital portal:** Per role map, these can stay **web-only**. If you later add them on mobile: analytics (admin), incoming alerts and handoffs (hospital staff) with the same “do not touch backend/infra” rule.

You can **skip Phase 6** for the first release and only add it if product asks for it on mobile.

---

## 4. What We Will Not Do (Reminders)

- **Do not** edit or add files under `emergency-medical-triage/frontend/` (web is your colleague’s).
- **Do not** edit `emergency-medical-triage/src/`, `emergency-medical-triage/infrastructure/`, or any Python/Terraform/Lambda/Bedrock/Aurora/S3 code.
- **Do not** implement or change the voice interface.
- **Do not** add new backend APIs or infra; only consume existing (or agreed) endpoints above.
- **Do not** put API keys or secrets in the app; use tokens and build-time config for base URL.

---

## 5. Suggested Order to Start Working

1. **Create** `emergency-medical-triage/frontend/mobile-android/` and an empty Android (Kotlin + Compose) project.
2. **Implement Phase 1** (design system + app shell + offline banner).
3. **Implement Phase 2** (auth + language).
4. **Implement Phase 3** (triage wizard + report + offline triage).
5. **Implement Phase 4** (hospital match + navigation + handoff).
6. **Implement Phase 5** (RMP dashboard + guidance + learning).
7. **Phase 6** only if required for mobile.

Use this doc as the single reference for “what we’re going to do” for the Android app; when in doubt, keep scope to **mobile app frontend only** and do not disturb web, backend, or infra.
