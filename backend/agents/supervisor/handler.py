"""
CDSS Supervisor Agent — Lambda Handler
Central router for the multi-agent clinical decision support system.
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

# Define tools for the Supervisor Agent to route requests
ROUTING_TOOLS = [
    {
        "name": "route_to_patient_agent",
        "description": "Route requests related to patient records, history extraction, RAG-based summaries, or patient registration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The unique ID of the patient."},
                "intent": {"type": "string", "description": "The specific intent (e.g., 'get_summary', 'update_vitals')."},
                "context": {"type": "string", "description": "Brief context for the target agent."}
            },
            "required": ["intent"]
        }
    },
    {
        "name": "route_to_surgery_planning_agent",
        "description": "Route requests related to surgical protocols, pre-op/post-op checklists, or surgical requirement analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "surgery_id": {"type": "string", "description": "The unique ID of the surgery (if available)."},
                "patient_id": {"type": "string", "description": "The unique ID of the patient."},
                "intent": {"type": "string", "description": "The specific intent (e.g., 'generate_checklist', 'analyse_requirements', 'getChecklist', 'analyseSurgery', 'getProcedureGuidance')."},
                "context": {"type": "string", "description": "Brief context for the target agent."}
            },
            "required": ["intent"]
        }
    },
    {
        "name": "route_to_resource_agent",
        "description": "Route requests related to OT availability, equipment status, or bed management.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_type": {"type": "string", "enum": ["ot", "equipment", "bed"]},
                "intent": {"type": "string", "description": "The specific intent (e.g., 'check_availability', 'allocate')."},
                "context": {"type": "string", "description": "Brief context for the target agent."}
            },
            "required": ["resource_type", "intent"]
        }
    },
    {
        "name": "route_to_scheduling_agent",
        "description": "Route requests related to booking appointments, OT slots, or resolving schedule conflicts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "slot_time": {"type": "string", "description": "ISO format timestamp."},
                "intent": {"type": "string", "description": "The specific intent (e.g., 'book_appointment', 'resolve_conflict')."}
            },
            "required": ["intent"]
        }
    },
    {
        "name": "route_to_engagement_agent",
        "description": "Route requests related to reminders, consultation summaries, adherence, or escalations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "visit_id": {"type": "string"},
                "language": {"type": "string", "enum": ["English", "Hindi", "Tamil", "Telugu", "Bengali"]},
                "intent": {"type": "string", "description": "e.g. send_medication_reminder, generateSummary, trackAdherence, createReminders, escalate_alert."}
            },
            "required": ["intent"]
        }
    }
]

def handle_tool_call(tool_name, tool_input, session_id):
    """Execute routing logic by publishing events to the bus."""
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
    
    target_agent_map = {
        "route_to_patient_agent": "patient",
        "route_to_surgery_planning_agent": "surgery_planning",
        "route_to_resource_agent": "resource",
        "route_to_scheduling_agent": "scheduling",
        "route_to_engagement_agent": "engagement"
    }
    
    target_agent = target_agent_map.get(tool_name)
    if not target_agent:
        return f"Error: Unknown tool {tool_name}"
    
    # Record the routing decision in the session audit trail (DynamoDB + RDS)
    doctor_id = tool_input.get("doctor_id", "DR-UNKNOWN")
    patient_id = tool_input.get("patient_id")
    
    audit_logger.log_routing(
        session_id=session_id,
        intent=tool_input.get("intent", "unknown"),
        target_agent=target_agent,
        doctor_id=doctor_id,
        patient_id=patient_id
    )
    
    # Publish the event to EventBridge
    event_publisher.publish(
        source_agent="supervisor",
        event_type="AgentActionRequested",
        detail={
            "session_id": session_id,
            "action": tool_input.get("intent"),
            "params": tool_input,
            "target_agent": target_agent
        },
        target_agent=target_agent
    )
    
    return f"Routing request to {AGENT_NAMES[target_agent]} for action: {tool_input.get('intent')}."

def lambda_handler(event, context):
    """Main entry point for Supervisor Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Standardize input from API Gateway or Direct Call
    body = json.loads(event.get("body", "{}")) if "body" in event else event
    
    doctor_id = body.get("doctor_id", "DR-DEFAULT")
    session_id = body.get("session_id")
    user_message = body.get("message")
    patient_id = body.get("patient_id")
    
    if not user_message:
        return error_response("Message is required", 400)
    
    # Initialize or retrieve session
    if not session_id:
        session = session_manager.create_session(doctor_id, patient_id)
        session_id = session["session_id"]
    
    # Get recent conversation history
    history = session_manager.get_conversation_history(session_id)
    
    # Log user message
    session_manager.add_message(session_id, "user", user_message)
    
    try:
        # Invoke Bedrock with tool use capability
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["supervisor"],
            tools=ROUTING_TOOLS,
            conversation_history=history
        )
        
        agent_content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        
        # If there are tool calls, execute them (routing)
        tool_results = []
        for tool in tool_calls:
            result = handle_tool_call(tool["name"], tool["input"], session_id)
            tool_results.append(result)
        
        # Combine direct response and tool results
        final_text = agent_content
        if tool_results:
            if final_text:
                final_text += "\n\n"
            final_text += "Action: " + "; ".join(tool_results)
        
        # Log and store agent response
        session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["supervisor"])
        
        return success_response({
            "session_id": session_id,
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["supervisor"],
                metadata={
                    "tool_use": len(tool_calls) > 0,
                    "target_agents": [AGENT_NAMES[target_agent_map.get(t["name"])] for t in tool_calls if target_agent_map.get(t["name"])]
                }
            )
        })
        
    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}")
        return error_response(str(e), 500)
