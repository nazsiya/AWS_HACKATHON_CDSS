# CDSS Developer Onboarding (Req 7.4)

Welcome to the CDSS engineering team. Follow this guide to go from zero to a fully functional local development environment.

## 1. Prerequisites
- **Python 3.10+** (v3.12 recommended)
- **Node.js 18+** (v20 recommended)
- **AWS CLI** (Configured with `ap-south-1` and valid credentials for `cdss-dev`)
- **Git Bash** or **PowerShell Core**

## 2. Local Setup Checklist
1. [ ] **Clone the Repo**: `git clone <repo-url>`
2. [ ] **Venv Setup**:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate # Windows
   pip install -r src/requirements.txt
   ```
3. [ ] **Frontend Setup**:
   ```bash
   cd frontend/apps/doctor-dashboard
   npm install
   ```
4. [ ] **Credentials**: Ensure `.env` is populated (copy from `.env.example`).
5. [ ] **SSH Tunnel**: Start the DB tunnel for Aurora connectivity:
   ```powershell
   .\scripts\start_ssh_tunnel.ps1
   ```

## 3. Standard Verification Path
Run these commands to verify the core services are healthy:
- [ ] **Health**: `curl http://localhost:8080/health` (Should return `database: connected`)
- [ ] **API Tests**: `python scripts/run_phases_1_to_4_verify.ps1`
- [ ] **Alerts**: `python scripts/test_phase5_alerts.py`

## 4. Full Agent Flow Walkthrough
To verify the AI Supervisor:
1. Start the API local wrapper: `python scripts/run_api_local.py`.
2. Send a POST to `/agent`:
   ```json
   { "message": "Who is patient PT-1001?" }
   ```
3. Verify the AI identifies the patient intent and returns a record from Aurora.

---
*Questions? Reach out on #cdss-dev-support or check docs/PROJECT_REFERENCE.md.*
