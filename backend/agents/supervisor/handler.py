"""
CDSS Supervisor Agent — Lambda Handler
Central router for the multi-agent clinical decision support system.
"""

import json
import logging
import os
import sys
from typing import Optional, Tuple

# Add the lambda root to sys.path to import shared utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lambda Layers are mounted under /opt. Add them to sys.path so the `shared`
# package provided via the SharedLayer is importable at runtime.
sys.path.append('/opt')
sys.path.append('/opt/python')

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
        "description": "Route requests related to patient records, RAG-based patient history summaries, drug interaction checks, prescription drafts, suggested lab tests, and treatment plan generation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The unique ID of the patient."},
                "intent": {"type": "string", "description": "The specific intent (e.g., 'get_patient_summary', 'check_drug_interactions', 'generate_prescription', 'suggest_lab_tests', 'get_treatment_plan', or 'update_vitals')."},
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

TARGET_AGENT_MAP = {
    "route_to_patient_agent": "patient",
    "route_to_surgery_planning_agent": "surgery_planning",
    "route_to_resource_agent": "resource",
    "route_to_scheduling_agent": "scheduling",
    "route_to_engagement_agent": "engagement",
}


def _normalize_tool_input(inp):
    if inp is None:
        return {}
    if isinstance(inp, dict):
        return inp
    if isinstance(inp, str) and inp.strip():
        try:
            return json.loads(inp)
        except json.JSONDecodeError:
            return {}
    return {}


def _is_valid_patient_id(pid: str | None) -> bool:
    """CDSS patient IDs look like PT-1001 (optionally PT-1001-2)."""
    if not pid:
        return False
    s = str(pid).strip().upper()
    # PT-<digits> or PT-<digits>-<digits>
    return bool(__import__("re").match(r"^PT-\d+(?:-\d+)?$", s))


def _extract_patient_lambda_text(invoke_payload_raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse Lambda JSON response from Patient handler. Returns (assistant_text, error_hint).
    """
    try:
        out = json.loads(invoke_payload_raw)
    except json.JSONDecodeError:
        return None, "invalid JSON from Patient Lambda"

    if isinstance(out, dict) and out.get("errorMessage"):
        return None, str(out.get("errorMessage", "Lambda error"))[:500]

    if not isinstance(out, dict) or "body" not in out:
        return None, "unexpected Patient Lambda shape (no body)"

    body = out["body"]
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return None, "Patient body is not JSON"

    if not isinstance(body, dict):
        return None, None

    if body.get("error") or body.get("message"):
        msg = body.get("message") or body.get("error") or "Patient error"
        return None, str(msg)[:500]

    # Direct invocation shape: { response: { content, ... } }
    inner = body.get("response")
    if isinstance(inner, dict) and inner.get("content"):
        text = str(inner["content"]).strip()
        return (text if text else None), None

    # Action internal request shape: { status: "processed", result: "<text>" }
    if isinstance(body.get("result"), str) and body.get("result").strip():
        return str(body["result"]).strip(), None

    return None, None


def _invoke_patient_agent_sync(message: str, doctor_id: str) -> Optional[str]:
    """
    Optionally call the Patient Lambda in the same request so the UI gets a real reply,
    not only 'Routing request…'. Requires PATIENT_AGENT_FUNCTION_NAME on the Supervisor
    and lambda:InvokeFunction permission (see infra CDK).

    Note: Supervisor timeout must allow two Bedrock-style calls (supervisor + nested patient);
    if too low, this returns None and only the routing line appears in the UI.
    """
    fn = (os.environ.get("PATIENT_AGENT_FUNCTION_NAME") or "").strip()
    if not fn:
        return None
    try:
        import boto3
        from botocore.config import Config

        lam = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "ap-south-1"),
            config=Config(read_timeout=120, connect_timeout=10),
        )
        apigw_event = {
            "body": json.dumps({"message": message, "doctor_id": doctor_id}),
            "httpMethod": "POST",
            "headers": {"Content-Type": "application/json"},
            "requestContext": {"requestId": "supervisor-sync-invoke"},
        }
        out_raw = lam.invoke(
            FunctionName=fn,
            InvocationType="RequestResponse",
            Payload=json.dumps(apigw_event).encode("utf-8"),
        )
        if out_raw.get("FunctionError"):
            raw = out_raw["Payload"].read().decode("utf-8")
            logger.warning("Patient Lambda FunctionError: %s", raw[:2000])
            return None
        raw = out_raw["Payload"].read().decode("utf-8")
        text, err = _extract_patient_lambda_text(raw)
        if text:
            return text
        if err:
            logger.warning("Patient sync returned no assistant text: %s", err)
        return None
    except Exception as e:
        logger.warning("Sync Patient Lambda invoke failed (%s): %s", fn, e)
        return None


def _invoke_patient_agent_sync_action(
    action: str,
    params: dict,
    session_id: str,
    doctor_id: str,
) -> Optional[str]:
    """
    Invoke Patient Lambda with an internal AgentActionRequested payload so we can
    deterministically execute the tool handler and show the result immediately.
    """
    fn = (os.environ.get("PATIENT_AGENT_FUNCTION_NAME") or "").strip()
    if not fn:
        return None
    try:
        import boto3
        from botocore.config import Config

        lam = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "ap-south-1"),
            config=Config(read_timeout=90, connect_timeout=10),
        )

        apigw_event = {
            "body": json.dumps(
                {
                    "event_type": "AgentActionRequested",
                    "action": action,
                    "params": params,
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                }
            ),
            "httpMethod": "POST",
            "headers": {"Content-Type": "application/json"},
            "requestContext": {"requestId": "supervisor-sync-patient-action"},
        }

        out_raw = lam.invoke(
            FunctionName=fn,
            InvocationType="RequestResponse",
            Payload=json.dumps(apigw_event).encode("utf-8"),
        )
        if out_raw.get("FunctionError"):
            raw = out_raw["Payload"].read().decode("utf-8")
            logger.warning("Patient Lambda FunctionError: %s", raw[:2000])
            return None

        raw = out_raw["Payload"].read().decode("utf-8")
        text, err = _extract_patient_lambda_text(raw)
        if text:
            return text
        if err:
            logger.warning("Patient sync action returned no text: %s", err)
        return None
    except Exception as e:
        logger.warning("Sync Patient Lambda (action) invoke failed (%s): %s", fn, e)
        return None


def _invoke_surgery_planning_agent_sync_action(
    action: str,
    params: dict,
    session_id: str,
    doctor_id: str,
) -> Optional[str]:
    """
    Invoke SurgeryPlanning Lambda synchronously for routed tool actions.
    """
    fn = (os.environ.get("SURGERY_AGENT_FUNCTION_NAME") or "").strip()
    if not fn:
        return None
    try:
        import boto3
        from botocore.config import Config

        lam = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "ap-south-1"),
            config=Config(read_timeout=90, connect_timeout=10),
        )

        # SurgeryPlanningAgent expects internal routing fields at top-level (no `body` wrapper).
        payload_obj = {
            "event_type": "AgentActionRequested",
            "action": action,
            "params": params or {},
            "session_id": session_id,
            "doctor_id": doctor_id,
        }

        out_raw = lam.invoke(
            FunctionName=fn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload_obj).encode("utf-8"),
        )
        if out_raw.get("FunctionError"):
            raw = out_raw["Payload"].read().decode("utf-8")
            logger.warning("SurgeryPlanning Lambda FunctionError: %s", raw[:2000])
            return None

        raw = out_raw["Payload"].read().decode("utf-8")
        try:
            outer = json.loads(raw)
        except json.JSONDecodeError:
            return None

        # Lambda proxy response: {statusCode, headers, body}
        if isinstance(outer, dict) and "body" in outer:
            body = outer.get("body")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    return None
            if isinstance(body, dict):
                result = body.get("result")
                if isinstance(result, str) and result.strip():
                    return result.strip()
        return None
    except Exception as e:
        logger.warning("Sync SurgeryPlanning Lambda invoke failed (%s): %s", fn, e)
        return None


def handle_tool_call(tool_name, tool_input, session_id):
    """Execute routing logic by publishing events to the bus."""
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
    
    target_agent = TARGET_AGENT_MAP.get(tool_name)
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
    if "body" in event:
        raw_body = event.get("body")
        if isinstance(raw_body, dict):
            body = raw_body
        elif raw_body is None:
            body = {}
        else:
            # API Gateway normally provides `body` as a JSON string.
            try:
                body = json.loads(raw_body or "{}")
            except Exception:
                return error_response("Invalid JSON body", 400)
    else:
        body = event
    
    doctor_id = body.get("doctor_id", "DR-DEFAULT")
    session_id = body.get("session_id")
    user_message = body.get("message")
    patient_id = body.get("patient_id")
    user_message_lower = (user_message or "").lower()
    
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
            tool_input = _normalize_tool_input(tool.get("input"))
            result = handle_tool_call(tool["name"], tool_input, session_id)
            if tool.get("name") == "route_to_patient_agent":
                # Never trust Bedrock-provided patient_id; always use UI-selected patient_id when present.
                if isinstance(tool_input, dict) and patient_id and (
                    not _is_valid_patient_id(tool_input.get("patient_id"))
                ):
                    tool_input["patient_id"] = patient_id
                intent = (tool_input.get("intent") or "").lower()
                # Always execute the routed Patient action synchronously so the UI gets
                # real, conversational content (not only "Routing request…").
                sync_text = _invoke_patient_agent_sync_action(
                    action=intent,
                    params=tool_input,
                    session_id=session_id,
                    doctor_id=doctor_id,
                )
                if sync_text:
                    result = sync_text
            elif tool.get("name") == "route_to_surgery_planning_agent":
                if isinstance(tool_input, dict) and patient_id and (
                    not _is_valid_patient_id(tool_input.get("patient_id"))
                ):
                    tool_input["patient_id"] = patient_id
                intent = (tool_input.get("intent") or "").lower()
                sync_text = _invoke_surgery_planning_agent_sync_action(
                    action=intent,
                    params=tool_input,
                    session_id=session_id,
                    doctor_id=doctor_id,
                )
                if sync_text:
                    result = sync_text
            else:
                # For agents we are not executing synchronously (Resource/Scheduling/Engagement),
                # suppress routing-only text from the HTTP response to keep the chat conversational.
                result = ""

            if isinstance(result, str) and result.strip():
                tool_results.append(result)
            # else: skip empty results
        
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
                    "target_agents": [
                        AGENT_NAMES[TARGET_AGENT_MAP.get(t["name"])]
                        for t in tool_calls
                        if TARGET_AGENT_MAP.get(t["name"])
                    ],
                }
            )
        })
        
    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}")
        return error_response(str(e), 500)
