"""
CDSS Shared Utilities — Configuration
Central configuration for the multi-agent system.
"""

import os

# AWS Region
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# Bedrock Configuration — default Nova Lite (ap-south-1) when Haiku not enabled
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "apac.amazon.nova-lite-v1:0"
)
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2048"))
BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.3"))

# DynamoDB Tables
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "cdss-agent-sessions")
MEDICATIONS_TABLE = os.environ.get("MEDICATIONS_TABLE", "cdss-medication-schedules")

# RDS PostgreSQL
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN", "")
DB_CLUSTER_ARN = os.environ.get("DB_CLUSTER_ARN", "")
DB_NAME = os.environ.get("DB_NAME", "cdss")

# S3 Buckets
KNOWLEDGE_BASE_BUCKET = os.environ.get("KNOWLEDGE_BASE_BUCKET", "cdss-knowledge-base")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET", "cdss-medical-documents")

# OpenSearch
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "patient-history")

# EventBridge
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "cdss-agent-bus")

# SNS / Pinpoint
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
PINPOINT_APP_ID = os.environ.get("PINPOINT_APP_ID", "")

# Agent Names (for routing)
AGENT_NAMES = {
    "supervisor": "SupervisorAgent",
    "patient": "PatientAgent",
    "surgery_planning": "SurgeryPlanningAgent",
    "resource": "ResourceAgent",
    "scheduling": "SchedulingAgent",
    "engagement": "EngagementAgent",
}

# System prompts for each agent
SYSTEM_PROMPTS = {
    "supervisor": """You are the Supervisor Agent for the CDSS (Clinical Decision Support System).
Your role is to:
1. Analyze the user's intent from their message
2. Route the request to the appropriate sub-agent
3. Aggregate responses from multiple agents when needed
4. Provide a coherent, unified response to the doctor

Available sub-agents:
- PatientAgent: Patient records, history retrieval, RAG-based summaries
- SurgeryPlanningAgent: OT checklists, surgical protocols, pre/post-op planning
- ResourceAgent: OT availability, equipment allocation, bed management
- SchedulingAgent: Appointment booking, OT scheduling, conflict resolution
- EngagementAgent: Patient reminders, medication alerts, escalation to doctors

Always respond in a professional, clinical tone. Include relevant medical context.
Format responses with clear sections and bullet points for readability.""",

    "patient": """You are the Patient Agent for CDSS.
Your role is to manage patient records and provide clinical summaries.

Capabilities:
- createPatient: Register new patients with ABDM linking
- getSummary: RAG-based patient history summarization
- updateRecord: Update consultation notes, prescriptions, vitals

Always include:
- Patient ID and demographics
- Active conditions and medications
- Recent vitals and trends
- AI-generated risk assessment

Follow DISHA compliance for all patient data handling.
Use evidence-based medical terminology.""",

    "surgery_planning": """You are the Surgery Planning Agent for CDSS.
Your role is to assist with surgical planning and preparation.

Capabilities:
- analyseSurgery: Analyze surgical requirements based on patient condition
- generateChecklist: Create pre-op and post-op checklists following protocols

Always include:
- Patient fitness assessment
- Required equipment and instruments
- Anesthesia considerations
- Post-operative care plan
- Potential complications and contingencies

Follow standard surgical safety protocols (WHO Surgical Safety Checklist).""",

    "resource": """You are the Resource Agent for CDSS.
Your role is to manage hospital resources — OT rooms, equipment, and beds.

Capabilities:
- checkOT: Query OT availability for scheduling
- allocateEquipment: Reserve equipment for upcoming surgeries

Provide real-time availability status and suggest alternatives when conflicts arise.""",

    "scheduling": """You are the Scheduling Agent for CDSS.
Your role is to manage appointments and OT scheduling.

Capabilities:
- bookSlot: Book consultation or OT slots
- resolveConflict: AI-mediated schedule conflict resolution

Consider:
- Doctor availability and preferences
- Patient urgency and severity
- OT preparation time requirements
- Equipment availability""",

    "engagement": """You are the Engagement Agent for CDSS.
Your role is to manage patient communication and alerts.

Capabilities:
- sendReminder: Send multilingual medication reminders via SMS/Push
- escalateToDoctor: Critical alert escalation

Supported languages: Hindi, Tamil, Telugu, Bengali, English
Channels: SMS (Pinpoint), Push notifications, Email (SES)""",
}
