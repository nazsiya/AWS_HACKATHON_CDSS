"""
Supervisor agent – routes natural-language intents to specialized CDSS sub-agents.

CDSS has exactly 5 agents: Patient, Surgery, Resource, Scheduling, Engagement.
There is NO Triage agent.

POST /api/v1/supervisor (or POST /agent -> delegated here):
  Body: { "message": "...", "patient_id": "PT-xxx" (optional), "context": {} }
  1. Classify intent via Bedrock (or keyword fallback).
  2. Delegate to the matching sub-agent handler (Patient, Surgery, Resource,
     Scheduling, Engagement, Hospitals).
  3. When USE_AGENTCORE=true and AGENT_RUNTIME_ARN is set, invoke AgentCore
     Runtime instead of local Bedrock (AC-1 PoC; converse fallback).
  4. Return aggregated response with safety disclaimer and audit trace.

Per CDSS.mdc: trace_review, safety_disclaimer, no PHI in logs.
See docs/agentcore-implementation-plan.md Phases AC-1 through AC-4.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict

from cdss.api.handlers.common import json_response
from cdss.services.i18n import detect_language, get_request_language, translate_text

logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "AI is for clinical support only. All decisions require qualified "
    "medical judgment. This system does not replace a doctor."
)

_FALLBACK_MODEL_ID = "apac.amazon.nova-lite-v1:0"


def _truncate_text(value: str, limit: int) -> str:
    s = (value or "").strip()
    return s if len(s) <= limit else (s[:limit] + "…")


def _load_bedrock_model_and_region() -> tuple[str, str] | None:
    """Load Bedrock model/region from Secrets Manager; force Nova Lite if Anthropic is configured."""
    secret_name = (os.environ.get("BEDROCK_CONFIG_SECRET_NAME") or "").strip()
    region = os.environ.get("AWS_REGION", "ap-south-1")
    if not secret_name:
        return None
    try:
        import boto3

        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        config = json.loads(resp.get("SecretString", "{}"))
        model_id = (config.get("model_id") or _FALLBACK_MODEL_ID).strip()
        bedrock_region = (config.get("region") or region).strip()
        if model_id.lower().startswith("anthropic."):
            model_id = _FALLBACK_MODEL_ID
        return model_id, bedrock_region
    except Exception:
        return None


def _bedrock_converse_messages(system: str, messages: list[dict], max_tokens: int = 450) -> str:
    cfg = _load_bedrock_model_and_region()
    if cfg is None:
        return ""
    model_id, bedrock_region = cfg
    try:
        import boto3

        br = boto3.client("bedrock-runtime", region_name=bedrock_region)
        resp = br.converse(
            modelId=model_id,
            system=[{"text": system}],
            messages=messages,
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
        )
        content = resp.get("output", {}).get("message", {}).get("content", []) or []
        return next((c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")), "").strip()
    except Exception:
        return ""


def _doctor_chat_reply(message: str, history: list, patient_snapshot: dict | None) -> dict:
    """
    Fast path for the doctor-side AI Assistant: one Bedrock call (Nova Lite),
    grounded in the patient snapshot provided by the UI.
    """
    snapshot = patient_snapshot if isinstance(patient_snapshot, dict) else {}
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, default=str)

    # Keep history short for latency + relevance.
    trimmed = []
    if isinstance(history, list):
        for m in history[-8:]:
            if not isinstance(m, dict):
                continue
            role = (m.get("role") or "user").strip().lower()
            if role not in ("user", "assistant"):
                role = "user"
            text = _truncate_text(m.get("text") or m.get("content") or "", 800)
            if text:
                trimmed.append({"role": role, "content": [{"text": text}]})

    user_turn = _truncate_text(message or "", 900)
    messages = [*trimmed, {"role": "user", "content": [{"text": user_turn}]}]

    system = (
        "You are a clinical decision support assistant for doctors.\n"
        "Use ONLY the provided patient snapshot JSON and the conversation.\n"
        "If information is missing, explicitly say what is missing.\n"
        "Be concise, structured, and action-oriented. Avoid definitive diagnosis.\n\n"
        "Return the response in this format:\n"
        "## Summary\n"
        "- ...\n"
        "## Key risks / red flags\n"
        "- ...\n"
        "## Medications & interactions (if meds provided)\n"
        "- ...\n"
        "## Pre-op checklist (if surgery planned)\n"
        "- ...\n"
        "## Next steps\n"
        "- ...\n"
    )

    # Provide snapshot as an initial user message to keep the system prompt smaller.
    context_msg = {
        "role": "user",
        "content": [{"text": f"Patient snapshot JSON (authorised):\n{snapshot_json[:12000]}"}],
    }
    reply = _bedrock_converse_messages(system=system, messages=[context_msg, *messages], max_tokens=420)
    if not reply:
        reply = "AI is temporarily unavailable."
    return {"reply": reply, "safety_disclaimer": SAFETY_DISCLAIMER}

# Intent labels → agent domains
INTENT_LABELS = [
    "patient",       # Patient Agent: history, summaries, surgery readiness
    "surgery",       # Surgery Agent: classification, checklists, guidance
    "resource",      # Resource Agent: OTs, equipment, staff availability
    "scheduling",    # Scheduling Agent: booking, replacement, utilisation
    "engagement",    # Engagement Agent: medications, reminders, consultations
    "hospitals",     # Hospital data lookup within CDSS
    "general",       # General clinical chat
]


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: Dict[str, list[str]] = {
    "patient": ["patient", "history", "record", "summary", "readiness", "demographics", "allergy", "condition",
               "triage", "severity", "emergency", "urgency", "priority"],
    "surgery": ["surgery", "surgical", "checklist", "procedure", "instrument", "operation", "pre-op", "complication"],
    "resource": ["resource", "ot ", "equipment", "staff", "specialist", "availability", "inventory", "conflict"],
    "scheduling": ["schedule", "booking", "slot", "replacement", "workload", "utilisation", "utilization", "calendar"],
    "engagement": ["medication", "reminder", "adherence", "consultation", "transcript", "nudge", "prescription"],
    "hospitals": ["hospital", "facility", "referral", "nearest"],
}


def _classify_intent_keywords(message: str) -> str:
    """Fast keyword-based intent classification (fallback when Bedrock unavailable)."""
    msg = message.lower()
    scores: Dict[str, int] = {k: 0 for k in INTENT_LABELS}
    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg:
                scores[intent] += 1
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] == 0:
        return "general"
    return best


def _classify_intent_bedrock(message: str) -> str:
    """
    Use Bedrock Converse to classify the user message into one of INTENT_LABELS.
    Falls back to keyword classification on any failure.
    """
    try:
        import boto3

        secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME")
        region = os.environ.get("AWS_REGION", "ap-south-1")
        if not secret_name:
            return _classify_intent_keywords(message)

        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        config = json.loads(resp.get("SecretString", "{}"))
        model_id = config.get("model_id") or "apac.amazon.nova-lite-v1:0"
        bedrock_region = config.get("region") or region

        prompt = (
            "You are an intent classifier for a hospital Clinical Decision Support System.\n"
            "Classify the following user message into exactly ONE of these categories:\n"
            f"{', '.join(INTENT_LABELS)}\n\n"
            "Respond with the category name ONLY (one word, lowercase).\n\n"
            f"User message: {message[:500]}"
        )

        bedrock = boto3.client("bedrock-runtime", region_name=bedrock_region)
        response = bedrock.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 16, "temperature": 0.0},
        )
        output = response.get("output", {})
        content = output.get("message", {}).get("content", [])
        text = next((c.get("text", "") for c in content if c.get("text")), "").strip().lower()
        if text in INTENT_LABELS:
            return text
        # Try partial match
        for label in INTENT_LABELS:
            if label in text:
                return label
        return _classify_intent_keywords(message)
    except Exception as e:
        logger.debug("Bedrock intent classification failed: %s", e)
        return _classify_intent_keywords(message)


def _extract_patient_id_from_message(message: str) -> str:
    """
    If the user did not pass patient_id in the body, try to extract a patient ID from the message
    so we can return a single patient instead of the full list. Looks for patterns like PT-1015, PT-1001.
    """
    if not message or not message.strip():
        return ""
    # Match PT- followed by digits (and optional suffix like -001)
    m = re.search(r"\b(PT-\d+(?:-\d+)?)\b", message.strip(), re.IGNORECASE)
    return m.group(1).upper() if m else ""


def _resolve_patient_id_by_name(message: str) -> str:
    """
    When message mentions a patient by name (e.g. "summary of patient Harish Menon"), fetch the
    patient list and return the ID of the first patient whose name appears in the message.
    Returns empty string if no match.
    """
    stop = {"patient", "summary", "full", "detailed", "give", "me", "the", "of", "with", "id", "about", "for"}
    words = re.findall(r"[A-Za-z][a-z]+|[A-Z]{2,}", message)
    candidates = []
    for i, w in enumerate(words):
        if w.lower() in stop:
            continue
        phrase = " ".join(words[i : i + 3]).strip()
        if len(phrase) >= 4 and phrase.lower() not in stop:
            candidates.append(phrase)
    if not candidates:
        return ""
    try:
        from cdss.api.handlers.patient import handler as patient_handler
        event = _build_proxy_event("GET", "v1/patients")
        resp = patient_handler(event, None)
        parsed = _parse_handler_response(resp)
        patients = parsed.get("patients") if isinstance(parsed, dict) else []
        if not isinstance(patients, list):
            return ""
        for p in patients:
            if not isinstance(p, dict):
                continue
            name = (p.get("name") or "").strip()
            if not name:
                continue
            for phrase in candidates:
                if len(phrase) < 3:
                    continue
                if phrase.lower() in name.lower() or name.lower() in phrase.lower():
                    return (p.get("id") or "").strip()
        return ""
    except Exception:
        return ""


def _invoke_agentcore(message: str, intent: str, context: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Invoke Bedrock AgentCore Runtime for the classified intent.
    Returns parsed response dict or None if AgentCore is unavailable.
    """
    runtime_arn = (os.environ.get("AGENT_RUNTIME_ARN") or "").strip()
    if not runtime_arn:
        return None
    try:
        import uuid
        import boto3

        region = os.environ.get("AWS_REGION", "ap-south-1")
        client = boto3.client("bedrock-agentcore", region_name=region)
        payload = json.dumps({
            "prompt": message,
            "intent": intent,
            **context,
        }).encode("utf-8")
        session_id = str(uuid.uuid4())
        runtime_arn = os.environ.get("AGENT_RUNTIME_ARN", "").strip()
        if not runtime_arn:
            return None

        resp = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            contentType="application/json",
        )
        result = resp.get("response")
        if result is None:
            return None
        if hasattr(result, "read"):
            data = json.loads(result.read().decode("utf-8"))
        else:
            data = result if isinstance(result, dict) else {}
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("AgentCore Runtime invocation failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Local agent delegation (when AgentCore is disabled)
# ---------------------------------------------------------------------------

def _reply_with_bedrock_context(user_message: str, context_label: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    When Bedrock is configured, pass the DB data to Bedrock so it can answer using
    real Aurora data; return the model's reply. Otherwise return raw data for backward compatibility.
    """
    if os.environ.get("BEDROCK_CONFIG_SECRET_NAME"):
        try:
            from cdss.bedrock.chat import invoke_chat_with_context
            result = invoke_chat_with_context(user_message, context_label, data)
            return {"reply": result.reply, "safety_disclaimer": result.safety_disclaimer}
        except Exception as e:
            logger.warning("Bedrock context reply failed, returning raw data: %s", e)
    return data


def _delegate_to_local_agent(intent: str, message: str, patient_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the appropriate local handler based on classified intent.
    When Bedrock is configured, the DB result is passed to Bedrock so the agent can answer
    using real Aurora data (natural-language reply instead of raw JSON).
    For 'general' intent, use the Bedrock chat endpoint.
    """
    try:
        if intent == "patient":
            event = _build_proxy_event("GET", f"v1/patients/{patient_id}" if patient_id else "v1/patients")
            from cdss.api.handlers.patient import handler as patient_handler
            data = _parse_handler_response(patient_handler(event, None))
            return _reply_with_bedrock_context(message, "Patient record(s) from database", data)

        if intent == "surgery":
            event = _build_proxy_event("GET", "v1/surgeries")
            from cdss.api.handlers.surgery import handler as surgery_handler
            data = _parse_handler_response(surgery_handler(event, None))
            return _reply_with_bedrock_context(message, "Surgery data from database", data)

        if intent == "resource":
            event = _build_proxy_event("GET", "v1/resources")
            from cdss.api.handlers.resource import handler as resource_handler
            data = _parse_handler_response(resource_handler(event, None))
            return _reply_with_bedrock_context(message, "Resource/OT data from database", data)

        if intent == "scheduling":
            event = _build_proxy_event("GET", "v1/schedule")
            from cdss.api.handlers.scheduling import handler as scheduling_handler
            data = _parse_handler_response(scheduling_handler(event, None))
            return _reply_with_bedrock_context(message, "Schedule data from database", data)

        if intent == "engagement":
            event = _build_proxy_event("GET", "v1/medications")
            from cdss.api.handlers.engagement import handler as engagement_handler
            data = _parse_handler_response(engagement_handler(event, None))
            return _reply_with_bedrock_context(message, "Medications/engagement data from database", data)

        if intent == "hospitals":
            event = _build_proxy_event(
                "POST", "v1/hospitals",
                body=json.dumps({"severity": context.get("severity", "medium"), "limit": 5}),
            )
            from cdss.api.handlers.hospitals import hospitals_handler
            data = _parse_handler_response(hospitals_handler(event, None))
            return _reply_with_bedrock_context(message, "Hospital match data", data)

        # NOTE: Triage agent removed per CDSS architecture (5 agents only).
        # Former triage keywords (emergency, severity, urgency) now route to patient intent.

        # general – use chat
        from cdss.bedrock.chat import invoke_chat
        result = invoke_chat(message)
        return {
            "reply": result.reply,
            "safety_disclaimer": result.safety_disclaimer,
        }
    except Exception as e:
        logger.warning("Local agent delegation failed for intent=%s: %s", intent, e)
        return {"reply": f"The {intent} agent is currently unavailable.", "error": str(e)}


def _build_proxy_event(method: str, proxy: str, body: str | None = None) -> Dict[str, Any]:
    """Build a minimal API Gateway proxy event for internal delegation."""
    return {
        "httpMethod": method,
        "path": f"/api/{proxy}",
        "pathParameters": {"proxy": proxy},
        "body": body,
        "queryStringParameters": {},
        "requestContext": {},
    }


def _parse_handler_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Extract body from a Lambda-style response dict."""
    body = resp.get("body")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {"raw": body}
    if isinstance(body, dict):
        return body
    return resp


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Supervisor agent entry point.

    POST body: { "message": "...", "patient_id": "PT-xxx", "context": {} }
    Returns: { "intent", "agent", "data", "safety_disclaimer", "correlationId", "source", "duration_ms" }
    """
    correlation_id = str(uuid.uuid4())
    start = time.perf_counter()
    body: Dict[str, Any] = {}
    try:
        raw = event.get("body")
        if raw:
            body = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass

    message = (body.get("message") or body.get("prompt") or "").strip()
    patient_id = (body.get("patient_id") or body.get("patientId") or "").strip()
    extra_context = body.get("context") or {}
    history = body.get("history") or body.get("conversation") or []
    patient_snapshot = body.get("patient_snapshot") or (extra_context.get("patient_snapshot") if isinstance(extra_context, dict) else None)

    if not message and not history:
        return json_response(
            400,
            {"error": "message is required", "safety_disclaimer": SAFETY_DISCLAIMER},
            event=event,
        )

    # Fast doctor chat path: if UI provides a patient snapshot, do one grounded Nova Lite call.
    if patient_snapshot:
        data = _doctor_chat_reply(message or "(Continue)", history if isinstance(history, list) else [], patient_snapshot)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return json_response(
            200,
            {
                "intent": "doctor_chat",
                "agent": "supervisor",
                "data": data,
                "safety_disclaimer": data.get("safety_disclaimer", SAFETY_DISCLAIMER),
                "correlationId": correlation_id,
                "source": "local",
                "duration_ms": duration_ms,
            },
            event=event,
        )

    if not message:
        return json_response(
            400,
            {"error": "message is required", "safety_disclaimer": SAFETY_DISCLAIMER},
            event=event,
        )

    # 1. Detect language and classify intent
    request_lang = get_request_language(event)
    input_lang = detect_language(message) if request_lang == "en" else request_lang

    # Translate to English for intent classification if needed
    message_for_classification = message
    if input_lang != "en":
        message_for_classification = translate_text(message, "en", input_lang)

    intent = _classify_intent_bedrock(message_for_classification)

    # If intent is patient and no patient_id was provided, try to extract from message (e.g. "summary of PT-1015" or "patient Harish Menon")
    if intent == "patient" and not patient_id:
        patient_id = _extract_patient_id_from_message(message_for_classification)
    if intent == "patient" and not patient_id:
        patient_id = _resolve_patient_id_by_name(message_for_classification)

    # 2. Delegate
    use_agentcore = os.environ.get("USE_AGENTCORE", "").strip().lower() == "true"
    source = "local"
    data: Dict[str, Any] | None = None

    if use_agentcore:
        data = _invoke_agentcore(message_for_classification, intent, {"patient_id": patient_id, **extra_context})
        if data is not None:
            source = "agentcore"

    if data is None:
        data = _delegate_to_local_agent(intent, message_for_classification, patient_id, extra_context)
        source = "local"

    # 3. Translate response back to input language if needed
    if input_lang != "en" and isinstance(data, dict):
        for key in ("reply", "message", "safety_disclaimer"):
            if key in data and isinstance(data[key], str):
                data[key] = translate_text(data[key], input_lang, "en")

    # 4. Aggregate response
    duration_ms = int((time.perf_counter() - start) * 1000)

    # Structured audit trace (no PHI)
    logger.info(
        "Supervisor intent=%s source=%s duration_ms=%d",
        intent,
        source,
        duration_ms,
        extra={"intent": intent, "source": source, "duration_ms": duration_ms},
    )

    # Inter-agent event log (Req 8 audit)
    try:
        from cdss.services.event_log import log_agent_event
        log_agent_event(
            source_agent="supervisor",
            target_agent=f"{intent}_agent",
            action=f"delegate:{intent}",
            correlation_id=correlation_id,
            success=not (isinstance(data, dict) and "error" in data),
            duration_ms=duration_ms,
        )
    except Exception:
        pass  # Non-fatal

    return json_response(
        200,
        {
            "intent": intent,
            "agent": f"{intent}_agent",
            "data": data,
            "safety_disclaimer": data.get("safety_disclaimer", SAFETY_DISCLAIMER) if isinstance(data, dict) else SAFETY_DISCLAIMER,
            "correlationId": correlation_id,
            "source": source,
            "duration_ms": duration_ms,
        },
        event=event,
    )
