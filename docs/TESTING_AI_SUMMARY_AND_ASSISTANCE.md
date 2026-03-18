# Testing AI Summary and AI Assistance in the Dashboard

This guide explains **where** and **how** to test AI summary and AI assistance (chat) in the doctor dashboard, and how to verify the backend APIs.

---

## 1. Where They Live in the Dashboard

| Feature | Where to test | What it does |
|--------|----------------|--------------|
| **AI assistance (chat)** | **AI** in the sidebar → **AIChat** page | Free-form chat with the CDSS AI (Supervisor + Bedrock). Use for “Patient summary”, “Drug interactions”, treatment plans, lab interpretation, or any clinical question. |
| **AI summary (consultation)** | **Patients** → click a patient → **Patient consultation** page → **“▶ Start consultation”** | When you start a consultation, the backend generates an AI summary from the patient record and recent visits (Bedrock). It appears in the **“AI summary & recommendations”** block. |
| **AI summary (patient detail)** | **Patients** → click a patient → **Patient consultation** | The full patient view can show an **aiSummary** when you open a patient (from `GET /api/v1/patients/:id` if the backend returns it). |
| **AI summary (ad-hoc)** | Not in UI by default | Backend exposes **POST /api/ai/summarize** for arbitrary text/conversation summarization. You can test it via script or Swagger (see §4). |

---

## 2. Prerequisites

- **Backend API running**  
  From repo root:  
  `python scripts/run_api_local.py`  
  (or use your deployed API URL.)

- **Frontend using the API (not mock)**  
  In `frontend/apps/doctor-dashboard/.env.local` (or `.env`):
  - `VITE_API_URL=http://localhost:8080` (or your API URL)
  - `VITE_USE_MOCK=false`

- **Restart frontend**  
  After changing env: `npm run dev` in `frontend/apps/doctor-dashboard` and hard-refresh the browser (Ctrl+Shift+R).

- **Optional: Bedrock**  
  For **real** AI responses (not fallback message):
  - Local: Bedrock config in `config.json` or env (e.g. `BEDROCK_CONFIG_SECRET_NAME` / model enabled in AWS).
  - Deployed: Lambda has access to Bedrock and the secret is set.  
  If Bedrock is not configured, the agent may return a short fallback message and the consultation AI summary may be empty (backend still returns 200).

---

## 3. How to Test in the Dashboard

### 3.1 AI assistance (chat)

1. Open the dashboard and go to **AI** in the sidebar (or `/ai`).
2. You should see the **CDSS AI Assistant** welcome screen with quick prompts: “Patient Summary”, “Drug Interactions”, “Treatment Plans”, “Lab Interpretation”.
3. **Option A:** Click one of the prompts (e.g. “Patient Summary”).
4. **Option B:** Type in the input box (e.g. “List patients” or “Summarize patient PT-1001”) and press Enter or click the send button.
5. **Expect:**
   - **Mock mode (`VITE_USE_MOCK=true`):** A canned reply after ~1.5 s; no backend call.
   - **Live API, Bedrock OK:** A real reply from the Supervisor/Bedrock, plus a **safety disclaimer** under the message.
   - **Live API, Bedrock not configured:** A short fallback message (e.g. “Agent endpoint ready. Connect Bedrock for live responses.”) and possibly a disclaimer.
   - **Live API, error:** Red error message in the chat (e.g. “Error: Failed to get AI response.”). Check API is running and `VITE_API_URL` is correct.

### 3.2 AI summary (consultation)

1. Go to **Patients**.
2. Click a patient (e.g. from the list or a card) to open **Patient consultation** (`/patient/:patientId`).
3. In the consultation view, find **“▶ Start consultation”** and click it.
4. **Expect:**
   - **Mock mode:** After ~0.8 s, a fake AI summary appears in the **“AI summary & recommendations”** section (e.g. “Key findings: Blood pressure trending upward…”).
   - **Live API:** The app calls **POST /api/v1/consultations/start** with `patient_id` and `doctor_id`. The backend creates a visit and, if Bedrock is available, generates an AI summary from the patient and recent visits. The response fields `summary` or `ai_summary` are shown in the same block. If Bedrock is not configured, the block may be empty (backend still returns 200 with `summary: ""`).
5. You can then add notes and click **Save consultation notes**; the saved consultation will include the AI summary in history.

### 3.3 Quick checklist in the UI

- [ ] **AI** page loads; no console errors.
- [ ] With **VITE_USE_MOCK=false** and API running: sending a message in **AI** returns a reply (real or fallback) and optionally a safety disclaimer.
- [ ] **Patients** → open a patient → **Start consultation**: the **“AI summary & recommendations”** section updates (mock text or backend-generated summary).

---

## 4. Verifying the Backend APIs (Without the UI)

You can confirm the AI endpoints work at the API level.

### 4.1 One-command test with mock data (no Aurora)

From repo root (PowerShell):

```powershell
.\scripts\test_ai_with_mock.ps1
```

This script:
- Unsets `DATABASE_URL` so the API uses **mock data** (no tunnel or Aurora).
- Starts the API in a new window (or uses it if already running on 8080).
- Runs Phase 4 verification (health, POST /agent, POST /api/ai/summarize).
- Prints a short **conversation**: two AI chat replies (“List patients”, “Drug interactions”) and one AI summary reply.

If the API is already running with mock data:

```powershell
.\scripts\test_ai_with_mock.ps1 -NoLaunchApi
```

For **interactive** chat after the test, run in the same terminal: `.\scripts\chat_agent_powershell.ps1`.

### 4.2 Run the Phase 4 verification script

With the API already running (e.g. on 8080 or 8081):

**PowerShell (repo root):**

```powershell
$env:BASE_URL = "http://localhost:8080"
python scripts/verify_phase4_ai.py
```

If your API is on another port:

```powershell
$env:BASE_URL = "http://localhost:8081"
python scripts/verify_phase4_ai.py
```

The script checks:

1. **GET /health** → 200.
2. **POST /agent** (AI chatbot) → 200, response has `reply` or `intent`, and optionally `safety_disclaimer`.
3. **POST /api/ai/summarize** → 200, response has `summary` and optionally `safety_disclaimer`.

If all pass, the script prints **OK: AI summary and AI chatbot endpoints working.**

### 4.3 Interactive conversation in PowerShell

To have a **back-and-forth conversation** with the AI from the terminal:

**PowerShell (repo root):**

```powershell
# Terminal 1: start the API
$env:PYTHONPATH = "src"; python scripts/run_api_local.py

# Terminal 2: interactive chat (default http://localhost:8080)
.\scripts\chat_agent_powershell.ps1
```

If the API runs on another port (e.g. 8081):

```powershell
$env:BASE_URL = "http://localhost:8081"; .\scripts\chat_agent_powershell.ps1
```

Type a message and press Enter; the script prints the AI reply (and safety disclaimer). Empty line to exit.

**Alternative (Python):** `python scripts/chat_agent_interactive.py` — same flow, uses `CDSS_AGENT_URL` or `http://localhost:8080/agent` by default.

### 4.4 Manual curl examples

**AI chat (agent):**

```powershell
curl -X POST http://localhost:8080/agent -H "Content-Type: application/json" -d "{\"message\": \"List patients\"}"
```

**AI summary (ad-hoc text):**

```powershell
curl -X POST http://localhost:8080/api/ai/summarize -H "Content-Type: application/json" -d "{\"text\": \"Patient has hypertension. On amlodipine 5mg. Last BP 138/88.\"}"
```

**Consultation start (triggers consultation AI summary):**

```powershell
curl -X POST http://localhost:8080/api/v1/consultations/start -H "Content-Type: application/json" -d "{\"patient_id\": \"PT-1001\", \"doctor_id\": \"DR-001\"}"
```

Expect JSON with `summary` or `ai_summary` in the consultation-start response when Bedrock is configured.

---

## 5. Mock vs live behaviour

| Scenario | AI chat (AIChat) | Consultation AI summary (Start consultation) |
|----------|------------------|-----------------------------------------------|
| **VITE_USE_MOCK=true** | Canned replies for the four prompts; generic reply for other messages. No API calls. | Fake summary after ~0.8 s. No API call. |
| **VITE_USE_MOCK=false**, API down | “Error: Cannot reach API…” (or similar). | Start consultation fails or never finishes; no summary. |
| **VITE_USE_MOCK=false**, API up, Bedrock not configured | Fallback message; may still have a safety disclaimer. | Backend returns 200 with empty `summary`/`ai_summary`; block may be empty. |
| **VITE_USE_MOCK=false**, API up, Bedrock configured | Real Supervisor/Bedrock reply and safety disclaimer. | Backend returns 200 with generated `summary`/`ai_summary`; shown in “AI summary & recommendations”. |

---

## 6. Is Bedrock configured?

**Yes, if:**

- **POST /api/ai/summarize** returns a real clinical summary (e.g. “The patient has hypertension and is currently taking amlodipine…”) and a safety disclaimer → Bedrock is used for summarization.
- **POST /agent** returns a natural-language reply and a safety disclaimer → Bedrock is formatting the response. The *content* of the reply (e.g. “internal server error”, “patient records”, or actual patient names) comes from **upstream data** (Supervisor → patient/surgery agent). So “internal server error” in the reply means the patient agent returned an error; Bedrock is still working and turning that into readable text.

**How to confirm locally:**

- Repo root has **config.json** with `bedrock_config_secret_name` (e.g. `cdss-dev/bedrock-config`), or **.env** has `BEDROCK_CONFIG_SECRET_NAME`. The secret in AWS Secrets Manager must contain `model_id` and `region` (see [BEDROCK_LOCAL_SETUP.md](BEDROCK_LOCAL_SETUP.md)).
- Run `.\scripts\test_ai_with_mock.ps1`. If **AI summary** shows a short clinical summary and **AI chat** shows any reply with a safety disclaimer, Bedrock is in use. If the chat reply says *“Bedrock is not configured”*, set the secret name and restart the API.

---

## 7. Troubleshooting

- **“Cannot reach API”**  
  Ensure the API is running and `VITE_API_URL` matches (no trailing slash). Restart the frontend after changing env.

- **AI chat shows error or fallback every time**  
  Run `scripts/verify_phase4_ai.py`; if POST /agent fails or returns no reply, check backend logs and Bedrock/Secrets Manager config (see PRE_BUILD_CHECKLIST.md).

- **Consultation “AI summary & recommendations” always empty (live API)**  
  Backend may not have Bedrock configured or the patient may have no data. Check that POST /api/v1/consultations/start returns a non-empty `summary` or `ai_summary` for a known patient (e.g. PT-1001) when Bedrock is set up.

- **CORS errors when using deployed API from localhost**  
  Ensure the deployed API allows your frontend origin (e.g. `http://localhost:5173`) in CORS, or test the same flows from the deployed frontend URL.

---

## 8. References

- **API endpoints:** [OPENAI_API_ENDPOINTS.md](OPENAI_API_ENDPOINTS.md), [FRONTEND_API_ENDPOINTS.md](FRONTEND_API_ENDPOINTS.md)
- **Frontend env:** [FRONTEND_API_AND_ENV.md](FRONTEND_API_AND_ENV.md)
- **Phase 4 verification:** `scripts/verify_phase4_ai.py`, `scripts/run_phase4_verify.ps1`
