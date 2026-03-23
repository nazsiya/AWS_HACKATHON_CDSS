# AI Hackathon - Clinical Decision Support System (CDSS)

An AI-powered healthcare platform for Indian hospitals that combines role-based access control with specialized AI agents for patient management, surgical support, resource optimization, and clinical decision support.

> AWS Hackathon Project | Region: ap-south-1 (Mumbai)

## Demo Instructions

### Live URLs
| Role | URL |
|------|-----|
| **Doctor Dashboard** | http://cdss-dev-746412758276.s3-website.ap-south-1.amazonaws.com |
| **Patient Portal** | http://cdss-dev-corpus-746412758276.s3-website.ap-south-1.amazonaws.com |

### Login Credentials
| Role | Email | Password |
|------|-------|----------|
| **Doctor** | doc2@cdss.ai | Demo@1234 |
| **Patient** | patient@cdss.ai | Demo@1234 |

### Demo Flow
1. Open Doctor Dashboard and login with doctor credentials
2. Click **Dashboard** - view patient queue with AI alerts
3. Click a patient - view vitals, history, AI recommendations
4. Click **AI Assistant** - test Bedrock AI agent queries
5. Open Patient Portal and login with patient credentials

## Live API Endpoints

| Endpoint | URL |
|----------|-----|
| **Base URL** | https://i3ecgd8x2g.execute-api.ap-south-1.amazonaws.com/prod/ |
| **Dashboard** | https://i3ecgd8x2g.execute-api.ap-south-1.amazonaws.com/prod/dashboard |
| **Health Check** | https://i3ecgd8x2g.execute-api.ap-south-1.amazonaws.com/prod/health |

## Overview

The Clinical Decision Support System (CDSS) provides:

- **Role-based access** - Doctor Module (full clinical access) and Patient Module (personal health only)
- **Five AI agents** - Patient, Surgery, Resource, Scheduling, and Patient Engagement agents communicating via Model Context Protocol (MCP)
- **India-first** - Multilingual support (Hindi, English, regional languages), cultural adaptation, and resource-aware design
- **Unified workflows** - Patient history, surgery readiness, medication adherence, real-time surgical support, and automated specialist replacement

## Repository Structure
```
AI_Hackathon_CDSS/
├── apps/
│   └── doctor-dashboard/     # React doctor UI
├── backend/                  # Python Lambdas
├── infra/                    # CDK infrastructure
├── scripts/                  # Utility scripts
├── clinical-decision-support-system/
│   ├── requirements.md
│   ├── design.md
│   └── implementation-plan.md
├── .env.example              # Environment variable templates
├── .gitignore
└── README.md
```

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS CLI configured with ap-south-1 access
- Docker (optional, for local DB)

### Setup
```powershell
# 1. Clone the repo
git clone https://github.com/priyankaVenkateshan/AI_Hackathon_CDSS
cd AI_Hackathon_CDSS

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install backend dependencies
pip install -r backend\agents\requirements.txt

# 4. Copy and configure environment variables
copy .env.example .env
# Edit .env with your actual values
```

### Running the Frontend
```powershell
cd frontend\apps\doctor-dashboard
npm install
npm run dev
```

## Python Virtual Environment

All Python dependencies must be installed only inside the project virtual environment (no global pip install).
```powershell
# Activate
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\agents\requirements.txt

# Or without activating
.\.venv\Scripts\pip.exe install -r backend\agents\requirements.txt
```

## Key Capabilities

- **Patient Agent** - Patient profiles, surgery readiness, medical history, multilingual data
- **Surgery Agent** - Surgery classification, requirements, checklists, real-time procedural support
- **Resource Agent** - Staff, OT, and equipment availability; conflict detection
- **Scheduling Agent** - Surgical scheduling and resource allocation
- **Patient Engagement Agent** - Conversation summaries, medication reminders, adherence tracking

## Documentation

| Document | Description |
|----------|-------------|
| [Requirements](clinical-decision-support-system/requirements.md) | User stories, acceptance criteria, and system requirements |
| [Design](clinical-decision-support-system/design.md) | Architecture, multi-agent design, RBAC, and integration details |

## License

See repository and project documentation for license and usage terms.
