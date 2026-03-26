"""
CDSS Surgery Planning Agent — Lambda Handler
Manages pre-operative and post-operative checklists and surgical procedure analysis.
"""

import json
import logging
import os
import sys

# Add the lambda root to sys.path to import shared utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/opt')
sys.path.append('/opt/python')

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

# Define tools for the Surgery Planning Agent (CDSS.mdc: pre_op_status, checklist_flags, requires_senior_review)
SURGERY_TOOLS = [
    {
        "name": "classify_surgery",
        "description": "Classify a surgery by type and complexity; returns pre_op_status and risk_factors for CDSS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "surgery_type": {"type": "string", "description": "Type of surgery (e.g., 'ACL Reconstruction')."},
                "patient_id": {"type": "string"},
                "patient_risk_factors": {"type": "string"}
            },
            "required": ["surgery_type"]
        }
    },
    {
        "name": "generate_pre_op_checklist",
        "description": "Generate a clinical pre-operative checklist for a specific surgery and patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "surgery_type": {"type": "string", "description": "Type of surgery (e.g., 'ACL Reconstruction')."},
                "preferences": {"type": "string", "description": "Any specific clinical preferences."}
            },
            "required": ["patient_id", "surgery_type"]
        }
    },
    {
        "name": "analyse_requirements",
        "description": "Analyze required equipment, instruments, and personnel for a specific surgery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "surgery_type": {"type": "string"},
                "patient_risk_factors": {"type": "string"}
            },
            "required": ["surgery_type"]
        }
    }
]

def _intent_to_surgery_tool(action):
    """Map Supervisor/API intents to Surgery Agent tool names (Phase 4)."""
    if not action:
        return "generate_pre_op_checklist"
    a = (action or "").strip().lower()
    if a in ("getchecklist", "generate_checklist", "generate_pre_op_checklist"):
        return "generate_pre_op_checklist"
    if a in ("analysesurgery", "analyse_requirements"):
        return "analyse_requirements"
    if a in ("getprocedureguidance", "procedure_guidance"):
        return "get_procedure_guidance"
    if a == "classify_surgery":
        return "classify_surgery"
    if a.startswith("generate") or a.startswith("get"):
        return "generate_pre_op_checklist"
    if a.startswith("analyse"):
        return "analyse_requirements"
    return "generate_pre_op_checklist"


def handle_tool_call(tool_name, tool_input, session_id):
    """Execute surgery-specific logic."""
    logger.info(f"Executing surgery tool: {tool_name} with input: {tool_input}")
    
    patient_id = tool_input.get("patient_id", "P-UNKNOWN")
    surgery_type = tool_input.get("surgery_type")
    
    # Log the action for DISHA compliance
    audit_logger.log_action(
        user_id="SYSTEM",
        action=f"SURGERY_AGENT_{tool_name.upper()}",
        resource_type="SURGERY",
        resource_id=tool_input.get("surgery_id"),
        details=tool_input,
        session_id=session_id
    )
    
    if tool_name == "classify_surgery":
        # CDSS.mdc: pre_op_status, risk_factors, requires_senior_review
        surgery_type = tool_input.get("surgery_type", "Unknown")
        risk_text = tool_input.get("patient_risk_factors", "")
        extracted = ai_service.extract_medical_entities(risk_text) if risk_text else {}
        risk_factors = [e["text"] for e in extracted.get("MEDICAL_CONDITION", [])] if isinstance(extracted, dict) else []
        if not risk_factors and risk_text:
            risk_factors = [risk_text[:200]]
        requires_senior_review = len(risk_factors) > 2
        out = {
            "surgery_type": surgery_type,
            "pre_op_status": "pending",
            "risk_factors": risk_factors,
            "requires_senior_review": requires_senior_review,
            "checklist_flags": ["Awaiting classification"],
            "safety_disclaimer": "AI is for support only. Clinical decisions require qualified judgment.",
        }
        event_publisher.publish_surgery_event(
            surgery_id=tool_input.get("surgery_id", "NEW-SRG"),
            status="classified",
            data=out,
        )
        # Return a conversational summary (not raw JSON) for the chat UI.
        risks = ", ".join(risk_factors) if risk_factors else "no explicit risk factors extracted"
        return (
            f"Surgery classification for {patient_id}:\n"
            f"- Surgery type: {surgery_type}\n"
            f"- Pre-op status: {out['pre_op_status']}\n"
            f"- Risk factors: {risks}\n"
            f"- Requires senior review: {'Yes' if out['requires_senior_review'] else 'No'}\n"
            f"\n{out['checklist_flags'][0]}\n"
            f"\nSafety disclaimer: {out['safety_disclaimer']}"
        )

    elif tool_name == "generate_pre_op_checklist":
        # CDSS.mdc: checklist_flags, pre_op_status, requires_senior_review
        checklist_items = [
            "Confirm patient identity, surgical site, and procedure.",
            "Ensure anesthesia machine and medication check are complete.",
            "Verify pulse oximeter is on patient and functioning.",
            "Confirm all team members have introduced themselves by name and role.",
            "Does the patient have a known allergy?",
            "Is the risk of aspiration or difficult airway assessed?",
        ]
        checklist = {
            "surgery": surgery_type,
            "patient_id": patient_id,
            "pre_op_status": "pending",
            "checklist": checklist_items,
            "checklist_flags": checklist_items,
            "estimated_duration": "120 minutes",
            "special_prep": "Prophylactic antibiotics administered 60 min before skin incision.",
            "requires_senior_review": False,
            "safety_disclaimer": "AI is for support only. Clinical decisions require qualified judgment.",
        }

        event_publisher.publish_surgery_event(
            surgery_id=tool_input.get("surgery_id", "NEW-SRG"),
            status="checklist_generated",
            data=checklist,
        )
        items = checklist["checklist"]
        numbered = "\n".join([f"- {x}" for x in items])
        return (
            f"Pre-op checklist for {patient_id} ({checklist['surgery']}):\n"
            f"{numbered}\n\n"
            f"Estimated duration: {checklist.get('estimated_duration')}\n"
            f"Special prep: {checklist.get('special_prep')}\n"
            f"Requires senior review: {'Yes' if checklist.get('requires_senior_review') else 'No'}\n\n"
            f"Safety disclaimer: {checklist.get('safety_disclaimer')}"
        )
        
    elif tool_name == "analyse_requirements":
        # Use AI Service to extract surgical requirements; CDSS-aligned output
        analysis = ai_service.extract_medical_entities(tool_input.get("patient_risk_factors", ""))
        extracted_risks = [e["text"] for e in analysis.get("MEDICAL_CONDITION", [])] if isinstance(analysis, dict) else []
        requirements = {
            "instruments": ["Orthopedic tray", "Arthroscopy tower"],
            "personnel": ["Main Surgeon", "Assistant Surgeon", "Anesthesiologist"],
            "extracted_risks": extracted_risks,
            "risk_factors": extracted_risks,
            "requires_senior_review": len(extracted_risks) > 2,
            "safety_disclaimer": "AI is for support only. Clinical decisions require qualified judgment.",
        }
        instruments = ", ".join(requirements.get("instruments") or [])
        personnel = ", ".join(requirements.get("personnel") or [])
        risks = ", ".join(requirements.get("risk_factors") or [])
        return (
            f"Surgery requirements for {patient_id}:\n"
            f"- Instruments: {instruments}\n"
            f"- Personnel: {personnel}\n"
            f"- Extracted risk factors: {risks if risks else 'none extracted'}\n"
            f"- Requires senior review: {'Yes' if requirements.get('requires_senior_review') else 'No'}\n\n"
            f"Safety disclaimer: {requirements.get('safety_disclaimer')}"
        )

    elif tool_name == "get_procedure_guidance":
        return (
            "Procedure guidance note:\n"
            "Real-time procedure guidance is available in the Surgery Planning screen (WebSocket-enabled flow).\n"
            f"Surgery ID: {tool_input.get('surgery_id') or 'unknown'}\n\n"
            "Safety disclaimer: AI is for support only. Clinical decisions require qualified judgment."
        )

    return f"Unknown surgery action: {tool_name}"

def lambda_handler(event, context):
    """Main entry point for Surgery Planning Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    detail = event.get("detail", event)
    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # Internal routing flow: map Supervisor intent to tool name
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        tool_name = _intent_to_surgery_tool(action)
        result = handle_tool_call(tool_name, params, session_id)
        session_manager.add_message(session_id, "assistant", f"[Surgery Agent Output]: {result}", agent=AGENT_NAMES["surgery_planning"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)
    
    try:
        response = bedrock.invoke_with_tools(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPTS["surgery_planning"],
            tools=SURGERY_TOOLS
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
            session_manager.add_message(session_id, "assistant", final_text, agent=AGENT_NAMES["surgery_planning"])

        return success_response({
            "response": agent_response(
                content=final_text,
                agent_name=AGENT_NAMES["surgery_planning"],
                metadata={"type": "surgical_analysis"}
            )
        })
        
    except Exception as e:
        logger.error(f"Surgery Planning Agent error: {e}")
        return error_response(str(e), 500)
