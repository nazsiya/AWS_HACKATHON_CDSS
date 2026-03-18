"""
CDSS Patient Agent — Lambda Handler
Manages patient records, history retrieval, and RAG-based clinical summaries.
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
    AIService,
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
ai_service = AIService()

# Define tools for the Patient Agent
PATIENT_TOOLS = [
    {
        "name": "get_patient_summary",
        "description": "Generate a clinical summary of the patient history using RAG context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The unique ID of the patient."},
                "time_frame": {"type": "string", "description": "Time frame for summary (e.g., 'last 6 months')."}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "update_vitals",
        "description": "Record new vital signs for a patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "vitals": {
                    "type": "object",
                    "properties": {
                        "hr": {"type": "integer", "description": "Heart rate in bpm."},
                        "bp": {"type": "string", "description": "Blood pressure (e.g., '120/80')."},
                        "spo2": {"type": "integer", "description": "Oxygen saturation (%)."},
                        "temp": {"type": "number", "description": "Temperature in Fahrenheit."}
                    }
                }
            },
            "required": ["patient_id", "vitals"]
        }
    },
    {
        "name": "get_lab_results",
        "description": "Retrieve recent lab results for a specific patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "test_type": {"type": "string", "description": "Specific test (e.g., 'CBC', 'HbA1c')."}
            },
            "required": ["patient_id"]
        }
    }
]

def handle_tool_call(tool_name, tool_input, session_id):
    """Execute patient-specific logic by interacting with data stores."""
    logger.info(f"Executing patient tool: {tool_name} with input: {tool_input}")
    
    patient_id = tool_input.get("patient_id", "P-UNKNOWN")
    
    # Log the action for DISHA compliance
    audit_logger.log_action(
        user_id="SYSTEM", # In worker mode, we might not have the doctor_id easily without passing it through
        action=f"PATIENT_AGENT_{tool_name.upper()}",
        resource_type="PATIENT",
        resource_id=patient_id,
        details=tool_input,
        session_id=session_id
    )
    
    if tool_name == "get_patient_summary":
        # Extract clinical entities from the history first
        # (In a real system, the text would come from the database)
        raw_history = "Patient has history of hypertension and Type 2 diabetes. Currently on Amlodipine 10mg."
        analysis = ai_service.analyze_clinical_text(raw_history)
        
        entities = analysis.get("entities", {})
        summary = (
            f"Clinical Summary for {patient_id}: Patient has documented "
            f"{', '.join([e['text'] for e in entities.get('MEDICAL_CONDITION', [])])}. "
            f"Active medications include {', '.join([e['text'] for e in entities.get('MEDICATION', [])])}."
        )
        return summary
        
    elif tool_name == "update_vitals":
        # Simulate updating the database
        vitals = tool_input.get("vitals")
        logger.info(f"Updating vitals for {patient_id}: {vitals}")
        
        # Publish event for other agents to know vitals updated
        event_publisher.publish_patient_update(
            patient_id=patient_id,
            update_type="vitals_updated",
            data={"vitals": vitals}
        )
        return f"Vital signs updated successfully for patient {patient_id}."
        
    elif tool_name == "get_lab_results":
        # Simulate lab result retrieval
        return f"Recent Lab Results for {patient_id}: HbA1c 7.8% (Feb 2024), Fasting Glucose 145 mg/dL (Jan 2024)."
    
    return f"Unknown patient action: {tool_name}"

def lambda_handler(event, context):
    """Main entry point for Patient Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Standardize input. This agent might be triggered directly from Supervisor 
    # or via EventBridge for async processing.
    detail = event.get("detail", event)
    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # If this is an action internal request from Supervisor (async flow)
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        tool_name = action if (action and action.startswith("get")) else "get_patient_summary"
        result = handle_tool_call(tool_name, params, session_id)
        
        # Update session history with the result
        session_manager.add_message(session_id, "assistant", f"[Patient Agent Output]: {result}", agent=AGENT_NAMES["patient"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)
    
    try:
        # Invoke Bedrock with tool use for the Patient Agent
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["patient"],
            tools=PATIENT_TOOLS
        )
        
        agent_content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        
        # Execute tool calls if any
        tool_outputs = []
        for tool in tool_calls:
            output = handle_tool_call(tool["name"], tool["input"], session_id)
            tool_outputs.append(output)
        
        # Build final response
        final_text = agent_content
        if tool_outputs:
            if final_text:
                final_text += "\n\n"
            final_text += "Action Results: " + "; ".join(tool_outputs)
            
        # Log to session if session_id is provided
        if session_id:
            session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["patient"])

        return success_response({
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["patient"],
                metadata={"type": "clinical_summary" if tool_outputs else "patient_query"}
            )
        })
        
    except Exception as e:
        logger.error(f"Patient Agent error: {e}")
        return error_response(str(e), 500)
