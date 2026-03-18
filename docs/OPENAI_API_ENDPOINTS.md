# CDSS AI & Bedrock Integration (Req 7.2)

This document outlines the AI endpoints, model configurations, and Bedrock usage within the CDSS platform. All responses include a safety disclaimer per project conventions.

## 1. Primary AI Entry Point (Supervisor)

| Endpoint | Handler | Purpose |
| :--- | :--- | :--- |
| `POST /agent` | supervisor | Central dispatch for natural language intents (patient, surgery, resource, scheduling, engagement). |
| `POST /api/v1/supervisor` | supervisor | Alias for API compliance. |

## 2. Bedrock Model Configuration

| Model / Config | Purpose | Environment / Secret |
| :--- | :--- | :--- |
| Claude / Nova (from secret) | Clinical processing, summaries, tool-use | `BEDROCK_CONFIG_SECRET_NAME` (model_id, region) |
| `amazon.titan-embed-text-v1` | Vector search / embeddings (MCP) | Optional `BEDROCK_EMBEDDING_ID` |

## 3. AI API Endpoints (`/api/ai/*`)

All served by `cdss.api.handlers.ai`; support both `/api/ai/...` and `/api/v1/ai/...` path forms.

| Endpoint | Purpose | Request body (key fields) | Response |
| :--- | :--- | :--- | :--- |
| `POST /api/ai/summarize` | Conversation/text summarization | `text`, `conversation` | `summary`, `safety_disclaimer` |
| `POST /api/ai/entities` | Medical entity extraction | `text` | `entities`, `safety_disclaimer` |
| `POST /api/ai/surgery-support` | Surgery guidance & checklist | `surgery_type`, `patient_id`, `context` | `guidance`, `checklist`, `safety_disclaimer` |
| `POST /api/ai/translate` | Multilingual translation (e.g. Hindi) | `text`, `target_lang`, `source_lang` | `translated`, `source_lang`, `target_lang` |
| `POST /api/ai/prescription` | AI-suggested prescription from history | `patient_id`, `conditions`, `history` | `suggestions`, `requires_approval`, `safety_disclaimer` |
| `POST /api/ai/adherence` | Medication adherence analysis | `patient_id`, `medications`, `history` | `adherence_score`, `risk_level`, `recommendations`, `alerts` |
| `POST /api/ai/engagement` | Patient engagement scoring | `patient_id`, `appointment_attendance`, `medication_adherence` | `engagement_score`, `alerts`, `recommendations` |
| `POST /api/ai/resources` | Health education resources for diagnosis | `diagnosis`, `symptoms` | `guides`, `recovery_plan`, `safety_disclaimer` |

## 4. Other AI-Related Endpoints

| Endpoint | Trigger / Logic | Description |
| :--- | :--- | :--- |
| `GET /api/v1/patients/:id` | Patient summary (Bedrock) | Clinical overview with extracted entities. |
| `GET /api/v1/terminology` | Approved terminology (i18n) | Hindi, Tamil (and other) terms for Phase 3.4 / R7. |

## 5. Safety & Formatting

Every AI response MUST include a safety disclaimer, e.g.:

> "AI is for clinical support only. All decisions require qualified medical judgment."

See `cdss.api.handlers.ai.SAFETY_DISCLAIMER` and project conventions.

---
*Environment: ap-south-1. OpenAPI: `docs/swagger.yaml`.*
