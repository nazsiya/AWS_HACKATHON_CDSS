# CDSS Architecture

## Overview

CDSS is a **multi-agent AI platform** for Indian hospitals, built on AWS in **ap-south-1 (Mumbai)**, **DISHA compliant** and **serverless-first**, with a target budget of **<$100/month**.

## High-Level Layers

| Layer | Components |
|-------|------------|
| **Frontend** | Doctor Dashboard (React/CloudFront), Patient App (React Native/Amplify), Surgery Planning UI, Admin (QuickSight), Voice (Transcribe), Multi-language (Translate), Medication Reminder (Amplify/Pinpoint), Auth (Cognito, WAF, JWT) |
| **API** | API Gateway (REST + WebSocket), ECS Fargate (real-time surgical WebSocket) |
| **Agents** | Supervisor + Patient, Surgery Planning, Resource, Scheduling, Engagement (Lambda + Bedrock) |
| **AI/ML** | Bedrock (Claude 3 Haiku), OpenSearch (RAG), Comprehend Medical, Transcribe |
| **Data** | RDS PostgreSQL, DynamoDB, S3, EventBridge, SNS Pinpoint |
| **MCP** | Clinical Protocols, Hospital Systems, ABDM/EHR, Telemedicine |
| **Security** | Secrets Manager, CloudWatch, CloudTrail, AES-256 |

## Agent Responsibilities

- **Supervisor**: `routeIntent`, `aggregateResponse`
- **Patient Agent**: History retrieval, RAG summaries, createPatient, getSummary, updateRecord
- **Surgery Planning Agent**: OT checklists, protocols, analyseSurgery, generateChecklist
- **Resource Agent**: OT availability, equipment, checkOT, allocateEquipment
- **Scheduling Agent**: Appointments, OT booking, bookSlot, resolveConflict
- **Engagement Agent**: Reminders, escalation, sendReminder, escalateToDoctor

## Data Flow

- **Sync**: Frontend → API Gateway → Lambda (router) → Agent → Bedrock / DynamoDB / RDS / OpenSearch
- **Async**: EventBridge (inter-agent messaging, DLQ), SNS Pinpoint (reminders), SES (escalation)

## Region & Compliance

- **Region**: ap-south-1 (Mumbai)
- **DISHA**: Audit logs (CloudWatch), consent, PHI handling
- **ABDM**: Health ID integration via ABDM/EHR MCP
