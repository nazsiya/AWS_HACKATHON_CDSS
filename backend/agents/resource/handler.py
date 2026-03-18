"""
CDSS Resource Agent — Lambda Handler
Manages hospital resources: OT rooms, equipment, and beds.
Real availability and allocation are served by GET/POST /api/v1/resources (Aurora + MCP).
This agent provides tool responses for Supervisor routing; for persistence use the API.
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

# Define tools for the Resource Agent
RESOURCE_TOOLS = [
    {
        "name": "check_resource_availability",
        "description": "Check the availability of OTs, equipment, or hospital beds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_type": {"type": "string", "enum": ["ot", "equipment", "bed"]},
                "start_time": {"type": "string", "description": "ISO format start time."},
                "end_time": {"type": "string", "description": "ISO format end time."}
            },
            "required": ["resource_type"]
        }
    },
    {
        "name": "allocate_resource",
        "description": "Reserve a resource for a specific surgery or patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "patient_id": {"type": "string"},
                "surgery_id": {"type": "string"}
            },
            "required": ["resource_id", "patient_id"]
        }
    }
]

def _intent_to_resource_tool(action):
    """Map Supervisor/API intents to Resource Agent tool names (Phase 5)."""
    if not action:
        return "check_resource_availability"
    a = (action or "").strip().lower()
    if a in ("check_availability", "check_resource_availability"):
        return "check_resource_availability"
    if a in ("allocate", "allocate_resource"):
        return "allocate_resource"
    if a.startswith("check"):
        return "check_resource_availability"
    if a.startswith("allocate"):
        return "allocate_resource"
    return "check_resource_availability"


def handle_tool_call(tool_name, tool_input, session_id):
    """Execute resource-specific logic."""
    logger.info(f"Executing resource tool: {tool_name} with input: {tool_input}")
    
    # Log the action for DISHA compliance
    audit_logger.log_action(
        user_id="SYSTEM",
        action=f"RESOURCE_AGENT_{tool_name.upper()}",
        resource_type="RESOURCE",
        resource_id=tool_input.get("resource_id", tool_input.get("resource_type")),
        details=tool_input,
        session_id=session_id
    )
    
    resource_type = tool_input.get("resource_type")
    
    if tool_name == "check_resource_availability":
        # Simulate availability check
        if resource_type == "ot":
            availability = [
                {"id": "OT-101", "name": "Main OT 1", "available": True},
                {"id": "OT-102", "name": "Cardiac OT", "available": False, "until": "2024-11-20T14:00:00Z"},
                {"id": "OT-103", "name": "Orthopedic OT", "available": True}
            ]
        elif resource_type == "equipment":
            availability = [
                {"id": "C-ARM-1", "name": "C-Arm Fluoroscopy", "available": True},
                {"id": "VENT-1", "name": "Ventilator V1", "available": True}
            ]
        else: # bed
            availability = {"total": 50, "occupied": 42, "available": 8}
            
        return json.dumps(availability)
        
    elif tool_name == "allocate_resource":
        # Simulate allocation
        resource_id = tool_input.get("resource_id")
        logger.info(f"Allocating resource {resource_id} to patient {tool_input.get('patient_id')}")
        return f"Resource {resource_id} has been successfully allocated."
    
    return f"Unknown resource action: {tool_name}"

def lambda_handler(event, context):
    """Main entry point for Resource Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    detail = event.get("detail", event)
    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # Internal routing flow: map Supervisor intent to tool name
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        tool_name = _intent_to_resource_tool(action)
        result = handle_tool_call(tool_name, params, session_id)
        session_manager.add_message(session_id, "assistant", f"[Resource Agent Output]: {result}", agent=AGENT_NAMES["resource"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)
    
    try:
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["resource"],
            tools=RESOURCE_TOOLS
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
            session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["resource"])

        return success_response({
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["resource"],
                metadata={"type": "resource_management"}
            )
        })
        
    except Exception as e:
        logger.error(f"Resource Agent error: {e}")
        return error_response(str(e), 500)
