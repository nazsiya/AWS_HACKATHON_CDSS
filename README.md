# AI Hackathon — Clinical Decision Support System (CDSS)

An AI-powered healthcare platform for Indian hospitals that combines role-based access control with specialized AI agents for patient management, surgical support, resource optimization, and clinical decision support.

## Where is everything?

- **This repo (plan, backend, infra)** — You are in the worktree: `...\AI_Hackathon_CDSS\agr`. It contains `clinical-decision-support-system/`, `infrastructure/`, `src/cdss/`, etc.
- **Doctor dashboard (frontend)** — It lives in **`D:\HACKATHON\CDSS-Frontend`** (separate folder).

**To have everything in one folder (e.g. `C:\AI_HACKATHON_CDSS` or `D:\AI_HACKATHON_CDSS`):**

1. Create a folder: `D:\AI_HACKATHON_CDSS` (or any path you want).
2. Copy the **entire contents** of this repo (agr) into it.
3. Copy the **entire contents** of `D:\HACKATHON\CDSS-Frontend` into the same folder (merge: you should get an `apps` folder with `doctor-dashboard`, a `backend` folder, and `infra` next to your existing `clinical-decision-support-system`, `infrastructure`, `src`).
4. Open `D:\AI_HACKATHON_CDSS` in Cursor/VS Code — you’ll see one project with plan, backend, infra, and frontend together.

## Overview

The Clinical Decision Support System (CDSS) provides:

- **Role-based access** — Doctor Module (full clinical access) and Patient Module (personal health only)
- **Five AI agents** — Patient, Surgery, Resource, Scheduling, and Patient Engagement agents communicating via Model Context Protocol (MCP)
- **India-first** — Multilingual support (Hindi, English, regional languages), cultural adaptation, and resource-aware design
- **Unified workflows** — Patient history, surgery readiness, medication adherence, real-time surgical support, and automated specialist replacement

## Repository Structure (after merging frontend)

```
AI_HACKATHON_CDSS/
├── apps/
│   └── doctor-dashboard/     # React doctor UI (from CDSS-Frontend)
├── backend/                  # Python Lambdas (from CDSS-Frontend)
├── infra/                    # CDK (from CDSS-Frontend)
├── clinical-decision-support-system/
│   ├── requirements.md
│   ├── design.md
│   └── implementation-plan.md
├── infrastructure/           # Terraform
├── src/
│   └── cdss/                # API handlers
├── .gitignore
└── README.md
```

## Documentation

| Document | Description |
|----------|-------------|
| [Requirements](clinical-decision-support-system/requirements.md) | User stories, acceptance criteria, and system requirements |
| [Design](clinical-decision-support-system/design.md) | Architecture, multi-agent design, RBAC, and integration details |

## Python and virtual environment

**All Python dependencies must be installed only inside the project virtual environment** (no global `pip install`).

- **Location:** `D:\AI_Hackathon_CDSS\.venv` (or `<repo>\.venv`). The venv lives on the same drive as the repo so it does not use C: space.
- **Backend dependencies:** Listed in `backend/agents/requirements.txt`. They are already installed in `.venv` (boto3, botocore, pydantic, python-dateutil, etc.).

**Use the venv for every Python/pip command:**

**PowerShell (Windows):**
```powershell
# Activate
.\.venv\Scripts\Activate.ps1

# Then run Python or pip (everything stays inside .venv)
pip install -r backend\agents\requirements.txt   # only if you add new deps
python -m your_module
```

**Or call the venv’s executables directly (no activate):**
```powershell
.\.venv\Scripts\pip.exe install -r backend\agents\requirements.txt
.\.venv\Scripts\python.exe -m your_module
```

**CMD (Windows):**
```cmd
.venv\Scripts\activate.bat
pip install -r backend\agents\requirements.txt
```

Do **not** run `pip install` or `python -m` without activating `.venv` or using `.venv\Scripts\pip.exe` / `.venv\Scripts\python.exe`, so that nothing is installed globally.

To (re)install backend dependencies into the venv only, from repo root run:
```powershell
.\scripts\install-python-deps.ps1
```

## Key Capabilities

- **Patient Agent** — Patient profiles, surgery readiness, medical history, multilingual data
- **Surgery Agent** — Surgery classification, requirements, checklists, real-time procedural support
- **Resource Agent** — Staff, OT, and equipment availability; conflict detection
- **Scheduling Agent** — Surgical scheduling and resource allocation
- **Patient Engagement Agent** — Conversation summaries, medication reminders, adherence tracking

## License

See repository and project documentation for license and usage terms.
