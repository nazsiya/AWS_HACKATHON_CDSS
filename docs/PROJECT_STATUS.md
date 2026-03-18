# CDSS Project Status & Roadmap

This document provides a comprehensive overview of the Clinical Decision Support System (CDSS) for Indian hospitals, detailing the work completed, the current architecture, and the remaining roadmap for production readiness.

---

## 🌟 Project Vision
An AI-powered multi-agent system designed to assist clinicians in Indian hospitals with patient management, surgical planning, and resource optimization.

---

## 🏗 System Architecture (5-Agent Model)
The system is powered by **Amazon Bedrock AgentCore**, using an orchestrator that routes requests to five specialized domains:

1.  **Patient Agent**: Manages clinical histories, summaries, and surgery readiness (ABDM integrated).
2.  **Surgery Agent**: Handles classification (e.g., Major/Minor), checklists, and procedural support.
3.  **Resource Agent**: Tracks OT availability, staff scheduling, and equipment status.
4.  **Scheduling Agent**: Manages surgical bookings and specialist replacements.
5.  **Engagement Agent**: Tracks medication adherence and sends patient reminders.

---

## ✅ What's Been Done (Completed)

### 🧩 AI & Logic
- **Orchestrator Implementation**: Multi-agent router in `agentcore/agent/cdssagent/src/main.py`.
- **Specialized Multi-Agent Prompts**: Custom prompts for all 5 domains with safety disclaimers.
- **Clinical Toolset**: 11 production-ready tools implemented in `infrastructure/gateway_tools_src/lambda_handler.py`.
- **Pydantic Validation**: Strict schema enforcement for all clinical outputs.
- **Confidence Scoring**: Automatic escalation to senior review if confidence < 0.85.

### 🗄 Backend & Data
- **RDS (Aurora) Integration**: Complete DB schema for Patients, Surgeries, Shifts, and Reminders.
- **Audit Trails**: Integrated event logging and alert engines in the DB.
- **Patient Constraints**: Unique `abha_id` enforcement for clinical safety.

### 🌐 Infrastructure & Documentation
- **AgentCore Setup**: AWS Runtime and Gateway configurations documented.
- **API Reference**: Comprehensive `api_reference.md` for all endpoints.
- **Testing Guides**: Integrated testing strategy for AWS and local environments.

---

## ⏳ What Needs To Be Done (Roadmap)

### 🛠 Technical Requirements (Priority 1)
- **Model Access**: Enable `Claude 3 Haiku` in the Bedrock console (required for stable tool-use).
- **IAM Refinement**: Attach `AmazonBedrockFullAccess` to the SDK Runtime role.
- **Real MCP Integration**: Transition from synthetic tool stubs to direct hospital/ABDM server connections.

### 🎨 UI & UX (Priority 2)
- **Frontend Connectivity**: Verify React/Vite dashboard connection to the AgentCore API.
- **Multilingual Support**: Expand agent responses to Hindi and regional languages.

### ⚖️ Safety & Compliance (Priority 3)
- **Trace Review**: Implement the medical audit dashboard for trace analysis.
- **RBAC Enforcement**: Finalize Cognito-based access for Doctor vs. Patient modules.

---

## 📂 Key Files to Explore
- [main.py](file:///d:/AI_Hackathon_CDSS/agentcore/agent/cdssagent/src/main.py): The brain of the multi-agent system.
- [lambda_handler.py](file:///d:/AI_Hackathon_CDSS/infrastructure/gateway_tools_src/lambda_handler.py): Implementation of all clinical tools.
- [PROJECT_REFERENCE.md](file:///d:/AI_Hackathon_CDSS/docs/PROJECT_REFERENCE.md): Single source of truth for IDs, ARNs, and constants.

---
> [!IMPORTANT]
> **Safety Disclaimer**: This system is for decision support only. All medical decisions require the judgment of a qualified clinician.
