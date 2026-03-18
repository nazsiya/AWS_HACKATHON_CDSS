"""
CDSS Scheduling Agent — Lambda Handler
Manages clinician appointments and OT scheduling.
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

# Define tools for the Scheduling Agent (Phase 6: find_replacement + SNS notify)
SCHEDULING_TOOLS = [
    {
        "name": "book_slot",
        "description": "Book a clinical appointment or OT slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "doctor_id": {"type": "string"},
                "slot_type": {"type": "string", "enum": ["appointment", "ot"]},
                "start_time": {"type": "string", "description": "ISO format start time."},
                "end_time": {"type": "string", "description": "ISO format end time."}
            },
            "required": ["patient_id", "slot_type", "start_time"]
        }
    },
    {
        "name": "get_doctor_schedule",
        "description": "Retrieve the current schedule for a specific doctor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string"},
                "date": {"type": "string", "description": "ISO format date (YYYY-MM-DD)."}
            },
            "required": ["doctor_id"]
        }
    },
    {
        "name": "find_replacement",
        "description": "Find replacement doctors for a surgery when the primary doctor is unavailable; optionally notify via escalation topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string", "description": "Unavailable doctor ID."},
                "surgery_id": {"type": "string", "description": "Surgery requiring replacement."},
                "date": {"type": "string", "description": "ISO date (YYYY-MM-DD)."},
                "notify": {"type": "boolean", "description": "If true, publish replacement request to doctor escalations SNS."}
            },
            "required": ["doctor_id", "surgery_id"]
        }
    }
]

def _intent_to_scheduling_tool(action):
    """Map Supervisor intent to Scheduling Agent tool name (Phase 6)."""
    if not action:
        return "get_doctor_schedule"
    a = (action or "").strip().lower()
    if a in ("find_replacement", "findreplacement"):
        return "find_replacement"
    if a in ("book_slot", "book_appointment"):
        return "book_slot"
    if a in ("get_doctor_schedule", "get_schedule"):
        return "get_doctor_schedule"
    if "replacement" in a:
        return "find_replacement"
    if "book" in a:
        return "book_slot"
    return "get_doctor_schedule"


def handle_tool_call(tool_name, tool_input, session_id):
    """Execute scheduling-specific logic."""
    logger.info(f"Executing scheduling tool: {tool_name} with input: {tool_input}")
    
    # Log the action for DISHA compliance
    audit_logger.log_action(
        user_id="SYSTEM",
        action=f"SCHEDULING_AGENT_{tool_name.upper()}",
        resource_type="SCHEDULE",
        resource_id=tool_input.get("doctor_id"),
        details=tool_input,
        session_id=session_id
    )
    
    doctor_id = tool_input.get("doctor_id")
    
    if tool_name == "book_slot":
        # Simulate booking
        slot_type = tool_input.get("slot_type")
        logger.info(f"Booking {slot_type} slot for doctor {doctor_id} at {tool_input.get('start_time')}")
        
        # Publish event for tracking/engagement
        event_publisher.publish(
            source_agent="scheduling",
            event_type="SlotBooked",
            detail=tool_input
        )
        return f"Successfully booked {slot_type} slot at {tool_input.get('start_time')}."
        
    elif tool_name == "get_doctor_schedule":
        # Simulate schedule retrieval
        schedule = [
            {"time": "09:00", "patient": "Rajesh Kumar", "type": "Consultation", "status": "Confirmed"},
            {"time": "10:30", "patient": "Ananya Singh", "type": "Follow-up", "status": "Confirmed"},
            {"time": "14:00", "patient": "Mohammed Farhan", "type": "Surgery Prep", "status": "In Progress"}
        ]
        return json.dumps(schedule)

    elif tool_name == "find_replacement":
        doctor_id = tool_input.get("doctor_id", "UNKNOWN")
        surgery_id = tool_input.get("surgery_id", "UNKNOWN")
        slot_date = tool_input.get("date", "")
        notify = tool_input.get("notify", True)
        # Simulate replacement list (real implementation would query RDS staff by specialty)
        replacements = [
            {"id": "ST-1", "name": "Dr. Meera Singh", "specialty": "Cardiology", "status": "available"},
            {"id": "ST-2", "name": "Dr. Arjun Nair", "specialty": "General Surgery", "status": "available"},
        ]
        if notify:
            try:
                import os
                import boto3
                topic_arn = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN")
                if topic_arn:
                    sns = boto3.client("sns")
                    sns.publish(
                        TopicArn=topic_arn,
                        Subject="CDSS: Replacement requested",
                        Message=f"Replacement requested for surgery {surgery_id}. Original doctor: {doctor_id}. Date: {slot_date}. Please assign from available staff."
                    )
            except Exception as e:
                logger.warning("SNS publish for replacement failed: %s", e)
        return json.dumps({
            "replacements": replacements,
            "surgery_id": surgery_id,
            "notified": notify,
            "message": "Replacement request sent to doctor escalations topic." if notify else "Replacement options listed."
        })

    return f"Unknown scheduling action: {tool_name}"

def lambda_handler(event, context):
    """Main entry point for Scheduling Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    detail = event.get("detail", event)
    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # Internal routing flow: map Supervisor intent to tool name
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        tool_name = _intent_to_scheduling_tool(action)
        result = handle_tool_call(tool_name, params, session_id)
        session_manager.add_message(session_id, "assistant", f"[Scheduling Agent Output]: {result}", agent=AGENT_NAMES["scheduling"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)
    
    try:
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["scheduling"],
            tools=SCHEDULING_TOOLS
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
            session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["scheduling"])

        return success_response({
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["scheduling"],
                metadata={"type": "slot_booking" if tool_outputs else "schedule_query"}
            )
        })
        
    except Exception as e:
        logger.error(f"Scheduling Agent error: {e}")
        return error_response(str(e), 500)
