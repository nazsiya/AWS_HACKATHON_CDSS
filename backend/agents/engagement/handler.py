"""
CDSS Engagement Agent — Lambda Handler
Manages patient communication, medication reminders, and clinical alerts.
"""

import json
import logging
import os
import sys

# Add the lambda root to sys.path to import shared utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    BedrockClient,
    SessionManager,
    EventPublisher,
    AuditLogger,
    success_response,
    error_response,
    agent_response,
    SYSTEM_PROMPTS,
    AGENT_NAMES,
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize shared components
bedrock = BedrockClient()
session_manager = SessionManager()
event_publisher = EventPublisher()
audit_logger = AuditLogger(session_manager)

# Define tools for the Engagement Agent
ENGAGEMENT_TOOLS = [
    {
        "name": "send_medication_reminder",
        "description": "Send a medication reminder to a patient in their preferred language.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "medication_name": {"type": "string"},
                "dosage": {"type": "string"},
                "language": {"type": "string", "enum": ["English", "Hindi", "Tamil", "Telugu", "Bengali"]}
            },
            "required": ["patient_id", "medication_name", "language"]
        }
    },
    {
        "name": "trigger_clinical_alert",
        "description": "Trigger a high-severity clinical alert for a doctor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                "message": {"type": "string"}
            },
            "required": ["patient_id", "severity", "message"]
        }
    },
    {
        "name": "generate_patient_summary",
        "description": "Request consultation summary for a visit (API POST /consultations/:visitId/generate-summary).",
        "input_schema": {"type": "object", "properties": {"visit_id": {"type": "string"}, "patient_id": {"type": "string"}}, "required": ["visit_id"]}
    },
    {
        "name": "track_adherence",
        "description": "Get adherence stats (API GET /reminders/adherence?patient_id=).",
        "input_schema": {"type": "object", "properties": {"patient_id": {"type": "string"}}, "required": ["patient_id"]}
    },
    {
        "name": "create_medication_reminders",
        "description": "Create medication reminders (API POST /reminders).",
        "input_schema": {"type": "object", "properties": {"patient_id": {"type": "string"}, "reminders": {"type": "array"}}, "required": ["patient_id", "reminders"]}
    }
]

def handle_tool_call(tool_name, tool_input, session_id):
    """Execute engagement-specific logic."""
    logger.info(f"Executing engagement tool: {tool_name} with input: {tool_input}")
    
    # Log the action for DISHA compliance
    audit_logger.log_action(
        user_id="SYSTEM",
        action=f"ENGAGEMENT_AGENT_{tool_name.upper()}",
        resource_type="PATIENT",
        resource_id=tool_input.get("patient_id"),
        details=tool_input,
        session_id=session_id
    )
    
    patient_id = tool_input.get("patient_id")
    
    if tool_name == "send_medication_reminder":
        # Simulate sending reminder via Pinpoint/SNS
        med_name = tool_input.get("medication_name")
        lang = tool_input.get("language")
        
        translations = {
            "Hindi": f"नमस्ते, कृपया अपनी दवा {med_name} लेना न भूलें।",
            "Tamil": f"வணக்கம், தயவுசெய்து உங்கள் மருந்து {med_name}-ஐ எடுத்துக் கொள்ள மறக்காதீர்கள்.",
            "English": f"Hello, please don't forget to take your medication: {med_name}."
        }
        
        message = translations.get(lang, translations["English"])
        logger.info(f"Sending {lang} reminder to {patient_id}: {message}")
        
        return f"Medication reminder ({lang}) sent successfully to patient {patient_id}."
        
    elif tool_name == "trigger_clinical_alert":
        # Simulate alert triggering
        severity = tool_input.get("severity")
        msg = tool_input.get("message")
        
        logger.warning(f"TRIGGERING {severity.upper()} ALERT for {patient_id}: {msg}")
        
        # Publish event for the dashboard to pick up
        event_publisher.publish_alert(
            alert_type="high_severity_clinical",
            severity=severity,
            message=msg,
            patient_id=patient_id
        )
        return f"Clinical {severity} alert triggered and routed to duty clinicians."

    elif tool_name == "generate_patient_summary":
        visit_id = tool_input.get("visit_id", "")
        return f"Call API POST /api/v1/consultations/{visit_id}/generate-summary to generate summary and entities."

    elif tool_name == "track_adherence":
        pid = tool_input.get("patient_id", "")
        return f"Call API GET /api/v1/reminders/adherence?patient_id={pid} for adherence stats."

    elif tool_name == "create_medication_reminders":
        pid = tool_input.get("patient_id", "")
        return f"Create reminders via API POST /api/v1/reminders with patient_id={pid}, scheduled_at, optional medication_id."

    return f"Unknown engagement action: {tool_name}"


def _intent_to_engagement_tool(action):
    """Map Supervisor intent to Engagement Agent tool (Phase 7)."""
    if not action:
        return "send_medication_reminder"
    a = (action or "").strip().lower()
    if "summary" in a:
        return "generate_patient_summary"
    if "adherence" in a:
        return "track_adherence"
    if "reminder" in a:
        return "send_medication_reminder"
    if "alert" in a or "escalat" in a:
        return "trigger_clinical_alert"
    return "send_medication_reminder"

def lambda_handler(event, context):
    """Main entry point for Engagement Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    detail = event.get("detail", event)
    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # Internal routing flow
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        tool_name = _intent_to_engagement_tool(action)
        result = handle_tool_call(tool_name, params, session_id)
        session_manager.add_message(session_id, "assistant", f"[Engagement Agent Output]: {result}", agent=AGENT_NAMES["engagement"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)
    
    try:
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["engagement"],
            tools=ENGAGEMENT_TOOLS
        )
        
        agent_content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        
        tool_outputs = []
        for tool in tool_calls:
            output = handle_tool_call(tool["name"], tool["input"], session_id)
            tool_outputs.append(output)
        
        final_text = agent_content
        if tool_outputs:
            if final_text:
                final_text += "\n\n"
            final_text += "Action Results: " + "; ".join(tool_outputs)
            
        if session_id:
            session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["engagement"])

        return success_response({
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["engagement"],
                metadata={"type": "patient_engagement"}
            )
        })
        
    except Exception as e:
        logger.error(f"Engagement Agent error: {e}")
        return error_response(str(e), 500)
