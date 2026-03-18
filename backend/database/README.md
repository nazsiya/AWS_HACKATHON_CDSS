# CDSS — Data Architecture

This repository contains the persistent storage definitions for the Clinical Decision Support System.

## Architecture

| Layer | Service | Purpose | Data Type |
|-------|---------|---------|-----------|
| **Relational** | RDS PostgreSQL | Patients, Surgeons, Surgery Plans, Consultations | Structured clinical data |
| **Document** | DynamoDB | Agent Sessions, Medication Schedules, Real-time Alerts | High-velocity, unstructured data |
| **Object** | S3 | DICOM Images, Lab Reports, Knowledge Base PDFs | Large binary medical files |
| **Semantic** | OpenSearch | Patient History Index, Medical Protocols Index | Vector search (RAG context) |

## Database Schema (PostgreSQL)

Located in `schema.sql`. Key tables:
- `patients`: Demographics and ward/bed status.
- `vitals_history`: Time-series vitals (HR, BP, SpO2).
- `surgery_plans`: Procedure definitions with agent-generated checklists.
- `consultations`: EHR data with AI-generated summaries.

## Real-time Data (DynamoDB)

Located in `dynamodb_tables.json`. Key tables:
- `cdss-agent-sessions`: PK `session_id`. Conversation history for all 6 agents.
- `cdss-medication-schedules`: Near real-time drug interaction tracking and reminders.
- `cdss-realtime-alerts`: Clinical alerts from AI and doctors.

## AIS (Ayushman Bharat Digital Mission)

The schema includes `abdm_id` for linking with the Indian Health Stack, ensuring DISHA compliance and interoperability.
