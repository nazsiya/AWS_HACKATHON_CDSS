"""
CDSS Patient Agent — Lambda Handler
Manages patient records, history retrieval, and RAG-based clinical summaries.
"""

import json
import logging
import os
import sys
from typing import Optional

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


def _get_db_connection():
    """Aurora/PostgreSQL using same contract as dashboard Lambda (RDS_CONFIG_SECRET_NAME)."""
    secret_name = (os.environ.get("RDS_CONFIG_SECRET_NAME") or "").strip()
    if not secret_name:
        return None
    try:
        import boto3
        import psycopg2

        sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        cfg = json.loads(sm.get_secret_value(SecretId=secret_name)["SecretString"])
        dbname = cfg.get("dbname") or cfg.get("database") or cfg.get("db") or "cdssdb"
        return psycopg2.connect(
            host=cfg.get("host") or cfg.get("hostname"),
            port=int(cfg.get("port", 5432)),
            database=dbname,
            user=cfg.get("username") or cfg.get("user"),
            password=cfg.get("password"),
            sslmode="require",
            connect_timeout=8,
        )
    except Exception as e:
        logger.warning("Patient agent DB connect skipped: %s", e)
        return None


def _build_clinical_summary_from_aurora(patient_id: str) -> Optional[str]:
    """Return a readable summary from RDS; None if unavailable or patient missing."""
    conn = _get_db_connection()
    if not conn:
        return None
    try:
        from psycopg2.extras import RealDictCursor

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT full_name, severity_level, status, gender, date_of_birth::text AS dob
                FROM patients WHERE patient_id = %s
                """,
                (patient_id,),
            )
            p = cur.fetchone()
            if not p:
                return f"No patient record found for **{patient_id}** in the hospital database."

            cur.execute(
                """
                SELECT medication_name, dosage, frequency, status, interactions_warning
                FROM medications
                WHERE patient_id = %s AND (status IS NULL OR LOWER(status) = 'active')
                ORDER BY medication_name
                LIMIT 20
                """,
                (patient_id,),
            )
            meds = cur.fetchall() or []

            cur.execute(
                """
                SELECT heart_rate, bp_systolic, bp_diastolic, spo2_percent, temperature_f, recorded_at
                FROM vitals_history
                WHERE patient_id = %s
                ORDER BY recorded_at DESC NULLS LAST
                LIMIT 1
                """,
                (patient_id,),
            )
            v = cur.fetchone()
    except Exception as e:
        logger.warning("Aurora summary query failed: %s", e)
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

    lines = [
        f"**{p['full_name']}** ({patient_id}) — {p['severity_level']} acuity, currently **{p['status']}**.",
        f"Demographics: {p.get('gender') or '—'}, DOB {p.get('dob') or '—'}.",
    ]
    if v:
        lines.append(
            f"Latest vitals: HR {v.get('heart_rate')} bpm, "
            f"BP {v.get('bp_systolic')}/{v.get('bp_diastolic')} mmHg, "
            f"SpO₂ {v.get('spo2_percent')}%, temp {v.get('temperature_f')} °F."
        )
    if meds:
        parts = []
        for m in meds:
            line = f"{m['medication_name']} {m['dosage']} ({m['frequency']})"
            if m.get("interactions_warning"):
                line += f" — note: {m['interactions_warning']}"
            parts.append(line)
        lines.append("Active medications: " + "; ".join(parts))
    else:
        lines.append("Active medications: none listed in EMR for this patient.")

    return "\n".join(lines)


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
    
    # Normalize common supervisor intent names
    tn = (tool_name or "").strip().lower()
    if tn in ("get_summary", "get_patient_summary", "getsummary"):
        tn = "get_patient_summary"

    if tn == "get_patient_summary":
        aurora = _build_clinical_summary_from_aurora(patient_id)
        if aurora:
            return aurora

        # Fallback when RDS is unavailable: Comprehend Medical + stub narrative (avoid empty ". ." strings)
        raw_history = (
            "Patient has history of hypertension and Type 2 diabetes. "
            "Currently on Metformin 500mg twice daily and Amlodipine 10mg once daily."
        )
        analysis = ai_service.analyze_clinical_text(raw_history)
        entities = analysis.get("entities") or {}
        if not isinstance(entities, dict):
            entities = {}

        conds = [e.get("text", "") for e in entities.get("MEDICAL_CONDITION", []) if e.get("text")]
        meds = [e.get("text", "") for e in entities.get("MEDICATION", []) if e.get("text")]
        cond_str = ", ".join(conds) if conds else "hypertension; Type 2 diabetes (stub narrative)"
        med_str = ", ".join(meds) if meds else "Metformin; Amlodipine (stub narrative)"
        return (
            f"Clinical Summary for {patient_id}: Patient has documented {cond_str}. "
            f"Active medications include {med_str}. "
            f"(EMR connection unavailable — showing analysis of sample clinical text.)"
        )
        
    elif tn in ("get_drug_interactions", "check_drug_interactions", "get_drug_interaction"):
        # Use stored interaction warnings from active medications.
        conn = _get_db_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT medication_name, interactions_warning
                        FROM medications
                        WHERE patient_id = %s
                          AND (status IS NULL OR LOWER(status) = 'active')
                          AND interactions_warning IS NOT NULL
                          AND TRIM(interactions_warning) <> ''
                        ORDER BY medication_name
                        LIMIT 20
                        """,
                        (patient_id,),
                    )
                    rows = cur.fetchall() or []
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            rows = []

        if rows:
            lines = [
                f"Potential interaction notes for {patient_id} (from EMR warnings):"
            ]
            for r in rows:
                lines.append(f"- {r.get('medication_name')}: {r.get('interactions_warning')}")
            lines.append("Recommend clinician review and consider renal function / contraindications where applicable.")
            return "\n".join(lines)
        return (
            f"No explicit interaction warnings were found in the EMR for active medications of {patient_id}. "
            "Clinician review is still recommended."
        )

    elif tn in ("generate_prescription", "get_prescription", "suggest_prescription"):
        # Educational prescription suggestion based on active meds.
        conn = _get_db_connection()
        meds = []
        severity = None
        status = None
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT severity_level, status FROM patients WHERE patient_id = %s",
                        (patient_id,),
                    )
                    p = cur.fetchone() or {}
                    severity = p.get("severity_level")
                    status = p.get("status")
                    cur.execute(
                        """
                        SELECT medication_name, dosage, frequency, status
                        FROM medications
                        WHERE patient_id = %s
                          AND (status IS NULL OR LOWER(status) = 'active')
                        ORDER BY medication_name
                        LIMIT 30
                        """,
                        (patient_id,),
                    )
                    meds = cur.fetchall() or []
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        med_lines = []
        for m in meds:
            med_lines.append(f"- {m.get('medication_name')} {m.get('dosage') or ''} ({m.get('frequency') or 'frequency not listed'})".strip())
        if not med_lines:
            med_lines = ["- No active medications were found in the EMR for this patient."]

        return (
            f"Prescription suggestion for {patient_id} (educational):\n"
            f"- Current clinical context: severity={severity or 'unknown'}, status={status or 'unknown'}\n"
            f"- Continue/consider regimen based on active EMR medications:\n"
            + "\n".join(med_lines)
            + "\n\n"
            "Note: This is not a real prescription. Final prescribing decisions require clinician review."
        )

    elif tn in ("suggest_lab_tests", "get_lab_results", "lab_interpretation"):
        # Suggest a standard lab panel; in a real system use conditions/diagnoses.
        return (
            f"Suggested lab tests for {patient_id}:\n"
            "- CBC\n"
            "- HbA1c (if diabetes/metabolic concerns)\n"
            "- Fasting / random glucose\n"
            "- Lipid panel\n"
            "- LFT (ALT/AST)\n"
            "- KFT (urea/creatinine/eGFR)\n"
            "- Electrolytes (Na/K)\n\n"
            "Note: Order tests based on clinician judgment and the patient's specific indications."
        )

    elif tn in ("get_treatment_plan", "generate_treatment_plan", "treatment_plan", "treatment plans", "treatment"):
        # Simple plan template based on severity/status + active meds.
        conn = _get_db_connection()
        severity = None
        status = None
        meds = []
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT severity_level, status FROM patients WHERE patient_id = %s",
                        (patient_id,),
                    )
                    p = cur.fetchone() or {}
                    severity = p.get("severity_level")
                    status = p.get("status")
                    cur.execute(
                        """
                        SELECT medication_name, dosage, frequency
                        FROM medications
                        WHERE patient_id = %s
                          AND (status IS NULL OR LOWER(status) = 'active')
                        ORDER BY medication_name
                        LIMIT 20
                        """,
                        (patient_id,),
                    )
                    meds = cur.fetchall() or []
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        med_str = (
            "; ".join(
                [f"{m.get('medication_name')} {m.get('dosage') or ''} ({m.get('frequency') or 'freq n/a'})".strip() for m in meds]
            )
            if meds
            else "no active meds listed in EMR"
        )

        return (
            f"Treatment plan for {patient_id} (educational template):\n"
            f"- Current acuity: {severity or 'unknown'}; current status: {status or 'unknown'}\n"
            f"- Medication focus: {med_str}\n"
            "- Goals (next 1-2 weeks):\n"
            "  - stabilize vitals within acceptable ranges\n"
            "  - improve symptom control and adherence\n"
            "- Monitoring:\n"
            "  - repeat vitals and key labs as clinically indicated\n"
            "  - check for adverse effects and drug-drug interaction warnings\n"
            "- Next steps:\n"
            "  - clinician follow-up and adjust regimen if targets are not met\n\n"
            "Note: This is clinical decision support; final care plan requires clinician judgment."
        )

    elif tn == "update_vitals":
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
        
    elif tn in ("get_lab_results",):
        # Simulate lab result retrieval
        return f"Recent Lab Results for {patient_id}: HbA1c 7.8% (Feb 2024), Fasting Glucose 145 mg/dL (Jan 2024)."
    
    return f"Unknown patient action: {tool_name}"


def _parse_patient_request(event):
    """
    Normalize API Gateway / Lambda.invoke (API-style) vs EventBridge vs direct payloads.
    Supervisor sync invoke sends { "body": "<json>", "httpMethod": "POST", ... }.
    """
    if "body" in event and event["body"] is not None:
        raw = event["body"]
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            return None
    if isinstance(event.get("detail"), dict):
        return event["detail"]
    return event


def lambda_handler(event, context):
    """Main entry point for Patient Agent."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    detail = _parse_patient_request(event)
    if detail is None:
        return error_response("Invalid JSON body", 400)

    session_id = detail.get("session_id", "SESS-INTERNAL")
    user_message = detail.get("message")
    
    # If this is an action internal request from Supervisor (async flow)
    if detail.get("event_type") == "AgentActionRequested":
        action = detail.get("action")
        params = detail.get("params", {})
        # Normalize supervisor action names to our handler tool names.
        a = (action or "").strip().lower()
        if a in ("get_summary", "get_patient_summary", "getsummary"):
            tool_name = "get_patient_summary"
        elif "interaction" in a:
            tool_name = "check_drug_interactions"
        elif "prescription" in a:
            tool_name = "generate_prescription"
        elif "lab" in a or "test" in a:
            tool_name = "suggest_lab_tests"
        elif "treatment" in a or "plan" in a:
            tool_name = "get_treatment_plan"
        else:
            # default summary handler
            tool_name = "get_patient_summary"
        result = handle_tool_call(tool_name, params, session_id)
        
        # Update session history with the result
        session_manager.add_message(session_id, "assistant", f"[Patient Agent Output]: {result}", agent=AGENT_NAMES["patient"])
        return success_response({"status": "processed", "result": result})

    if not user_message:
        return error_response("Message is required for direct invocation", 400)

    # Fast path: Supervisor sync summary (skip second Bedrock round-trip; stays under API Gateway ~29s budget)
    _sync_prefix = "Give a concise clinical summary for patient "
    if user_message.startswith(_sync_prefix):
        rest = user_message[len(_sync_prefix) :].strip().rstrip(".")
        patient_id = rest or "PT-1001"
        try:
            summary = handle_tool_call(
                "get_patient_summary", {"patient_id": patient_id}, session_id
            )
            return success_response({
                "response": agent_response(
                    content=summary,
                    agent_name=AGENT_NAMES["patient"],
                    metadata={"type": "clinical_summary", "sync": True},
                )
            })
        except Exception as e:
            logger.warning("Fast sync summary failed, falling back to Bedrock: %s", e)
    
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
