"""
AI service API handler – Bedrock/OpenAI wrappers for clinical AI actions.

POST /api/ai/summarize – conversation/text summarization
POST /api/ai/entities – medical entity extraction
POST /api/ai/surgery-support – surgery guidance and checklist
POST /api/ai/translate – multilingual translation (e.g. Hindi/regional)
POST /api/ai/prescription – AI-suggested prescription from patient history
POST /api/ai/adherence – medication adherence analysis
POST /api/ai/engagement – patient engagement scoring
POST /api/ai/resources – health education resources for diagnosis

Per project conventions: validated schemas, safety disclaimers, doctor-in-the-loop.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from cdss.api.handlers.common import json_response, parse_body_json

logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "AI is for clinical support only. All decisions require qualified medical judgment."
)
_FALLBACK_MODEL_ID = "apac.amazon.nova-lite-v1:0"


def _bedrock_converse(prompt: str, system: str, max_tokens: int = 600) -> str:
    """Call Bedrock Converse; return response text or empty string on failure."""
    secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME", "").strip()
    region = os.environ.get("AWS_REGION", "ap-south-1")
    if not secret_name:
        return ""
    try:
        import boto3
        sm = boto3.client("secretsmanager", region_name=region)
        raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
        cfg = json.loads(raw)
        model_id = (cfg.get("model_id") or _FALLBACK_MODEL_ID).strip()
        br_region = (cfg.get("region") or region).strip()
        if model_id.lower().startswith("anthropic."):
            model_id = _FALLBACK_MODEL_ID
    except Exception as e:
        logger.warning("AI: Bedrock config load failed: %s", e)
        return ""
    try:
        client = boto3.client("bedrock-runtime", region_name=br_region)
        resp = client.converse(
            modelId=model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt[:8000]}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
        )
        content = resp.get("output", {}).get("message", {}).get("content", []) or []
        return next((c.get("text", "") for c in content if isinstance(c, dict) and "text" in c), "").strip()
    except Exception as e:
        logger.warning("AI: Bedrock converse failed: %s", e)
        return ""


def _summarize(body: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize text or conversation."""
    text = (body.get("text") or "").strip()
    conversation = body.get("conversation") or []
    if not text and not conversation:
        return {"summary": "", "safety_disclaimer": SAFETY_DISCLAIMER, "error": "text or conversation required"}
    if conversation:
        parts = []
        for msg in conversation:
            role = msg.get("role", "user")
            content = msg.get("text") or msg.get("content") or str(msg)
            parts.append(f"{role}: {content}")
        text = "\n".join(parts)
    system = (
        "You are a clinical decision support assistant. Summarize the following conversation or text "
        "in 2–4 concise sentences. Do not add diagnosis or treatment advice; state only what was discussed."
    )
    summary = _bedrock_converse(text, system, max_tokens=400)
    # When Bedrock is not configured, provide a safe fallback so the UI always shows something
    if not summary or not summary.strip():
        excerpt = (text[:400] + "…") if len(text) > 400 else text
        summary = (
            "Summary (AI not configured): Key points from your notes — "
            + (excerpt.replace("\n", " ").strip() or "No content to summarize.")
        )
    return {"summary": summary, "safety_disclaimer": SAFETY_DISCLAIMER}


def _entities(body: Dict[str, Any]) -> Dict[str, Any]:
    """Extract medical entities (medications, conditions, etc.) from text."""
    text = (body.get("text") or "").strip()
    if not text:
        return {"entities": [], "safety_disclaimer": SAFETY_DISCLAIMER, "error": "text required"}
    system = (
        "You are a medical entity extractor. From the given clinical text, extract a JSON array of entities. "
        "Each item: {\"type\": \"medication\"|\"condition\"|\"procedure\"|\"lab\"|\"other\", \"value\": \"...\"}. "
        "Respond with ONLY the JSON array, no other text."
    )
    raw = _bedrock_converse(text, system, max_tokens=500)
    entities = []
    if raw:
        try:
            if raw.startswith("["):
                entities = json.loads(raw)
            else:
                for line in raw.split("\n"):
                    line = line.strip()
                    if line.startswith("["):
                        entities = json.loads(line)
                        break
            if not isinstance(entities, list):
                entities = []
        except json.JSONDecodeError:
            entities = [{"type": "other", "value": raw[:200]}]
    return {"entities": entities, "safety_disclaimer": SAFETY_DISCLAIMER}


def _surgery_support(body: Dict[str, Any]) -> Dict[str, Any]:
    """Surgery support guidance and checklist."""
    surgery_type = (body.get("surgery_type") or "").strip()
    context = (body.get("context") or "").strip()
    patient_id = (body.get("patient_id") or "").strip()
    prompt_parts = []
    if surgery_type:
        prompt_parts.append(f"Surgery type: {surgery_type}")
    if patient_id:
        prompt_parts.append(f"Patient ID: {patient_id}")
    if context:
        prompt_parts.append(f"Context: {context}")
    prompt = "\n".join(prompt_parts) or "General surgical support"
    system = (
        "You are a surgery support assistant. Provide brief pre-op and post-op checklist items and any relevant guidance. "
        "Use bullet points. Do not give definitive medical advice; recommend clinician review. "
        "Respond with: 1) Short guidance paragraph, 2) Checklist (bulleted list)."
    )
    guidance = _bedrock_converse(prompt, system, max_tokens=700)
    checklist = []
    if guidance:
        for line in guidance.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or (len(line) < 120 and line):
                checklist.append(line.lstrip("-* ").strip())
    return {
        "guidance": guidance or "Surgery support is temporarily unavailable.",
        "checklist": checklist or [],
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def _translate(body: Dict[str, Any]) -> Dict[str, Any]:
    """Translate text to target language; uses approved terminology list (Phase 3.4 / R7)."""
    text = (body.get("text") or "").strip()
    target_lang = (body.get("target_lang") or "hi").strip() or "hi"
    source_lang = (body.get("source_lang") or "en").strip() or "en"
    if not text:
        return {"translated": "", "source_lang": source_lang, "target_lang": target_lang, "error": "text required"}
    lang_names = {"en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali"}
    t_name = lang_names.get(target_lang, target_lang)
    s_name = lang_names.get(source_lang, source_lang)
    try:
        from cdss.services.i18n import get_approved_terminology_for_lang
        term_hint = get_approved_terminology_for_lang(target_lang)
    except Exception:
        term_hint = ""
    system = (
        f"You are a medical translator. Translate the following text from {s_name} to {t_name}. "
        "Preserve medical terminology where appropriate; use approved regional terms when known."
        f"{term_hint} "
        "Respond with ONLY the translated text, no preamble."
    )
    translated = _bedrock_converse(text, system, max_tokens=1000)
    return {
        "translated": translated or text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def _prescription(body: Dict[str, Any]) -> Dict[str, Any]:
    """AI-suggested prescription from patient history and conditions."""
    patient_id = (body.get("patient_id") or "").strip()
    conditions = body.get("conditions") or []
    history = (body.get("history") or body.get("text") or "").strip()
    prompt_parts = []
    if patient_id:
        prompt_parts.append(f"Patient ID: {patient_id}")
    if conditions:
        prompt_parts.append(f"Conditions: {', '.join(conditions) if isinstance(conditions, list) else conditions}")
    if history:
        prompt_parts.append(f"History: {history}")
    prompt = "\n".join(prompt_parts) or "General prescription assistance"
    system = (
        "You are a clinical decision support assistant. Based on the patient's conditions and history, "
        "suggest a draft prescription. Format as JSON array: [{\"medication\": \"...\", \"dosage\": \"...\", "
        "\"frequency\": \"...\", \"duration\": \"...\", \"notes\": \"...\"}]. "
        "Include standard disclaimers. Doctor must review and approve."
    )
    raw = _bedrock_converse(prompt, system, max_tokens=600)
    suggestions = []
    if raw:
        try:
            parsed = json.loads(raw if raw.startswith("[") else raw[raw.index("["):])
            if isinstance(parsed, list):
                suggestions = parsed
        except (json.JSONDecodeError, ValueError):
            suggestions = [{"medication": "See AI response", "notes": raw[:500]}]
    return {
        "suggestions": suggestions,
        "requires_approval": True,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def _adherence(body: Dict[str, Any]) -> Dict[str, Any]:
    """Medication adherence analysis and recommendations."""
    patient_id = (body.get("patient_id") or "").strip()
    medications = body.get("medications") or []
    history = (body.get("history") or body.get("text") or "").strip()
    prompt_parts = []
    if patient_id:
        prompt_parts.append(f"Patient ID: {patient_id}")
    if medications:
        prompt_parts.append(f"Current medications: {json.dumps(medications)}")
    if history:
        prompt_parts.append(f"Adherence history: {history}")
    prompt = "\n".join(prompt_parts) or "General adherence analysis"
    system = (
        "You are a medication adherence specialist. Analyze the patient's medication compliance and provide: "
        "1) adherence_score (0-100), 2) risk_level (low/medium/high), 3) recommendations (array of strings), "
        "4) alerts (array of strings for missed/critical items). "
        "Respond with ONLY valid JSON: {\"adherence_score\": N, \"risk_level\": \"...\", \"recommendations\": [...], \"alerts\": [...]}"
    )
    raw = _bedrock_converse(prompt, system, max_tokens=500)
    result = {"adherence_score": 0, "risk_level": "unknown", "recommendations": [], "alerts": []}
    if raw:
        try:
            parsed = json.loads(raw if raw.startswith("{") else raw[raw.index("{"):])
            if isinstance(parsed, dict):
                result.update(parsed)
        except (json.JSONDecodeError, ValueError):
            result["recommendations"] = [raw[:300]]
    result["safety_disclaimer"] = SAFETY_DISCLAIMER
    return result


def _engagement(body: Dict[str, Any]) -> Dict[str, Any]:
    """Patient engagement score, alerts, and recommendations."""
    patient_id = (body.get("patient_id") or "").strip()
    attendance = body.get("appointment_attendance") or {}
    adherence_data = body.get("medication_adherence") or {}
    prompt_parts = []
    if patient_id:
        prompt_parts.append(f"Patient ID: {patient_id}")
    if attendance:
        prompt_parts.append(f"Appointment attendance: {json.dumps(attendance)}")
    if adherence_data:
        prompt_parts.append(f"Medication adherence: {json.dumps(adherence_data)}")
    prompt = "\n".join(prompt_parts) or "General engagement assessment"
    system = (
        "You are a patient engagement analyst. Based on the data, compute: "
        "1) engagement_score (0-100), 2) alerts (array), 3) recommendations (array). "
        "Respond with ONLY valid JSON: {\"engagement_score\": N, \"alerts\": [...], \"recommendations\": [...]}"
    )
    raw = _bedrock_converse(prompt, system, max_tokens=400)
    result = {"engagement_score": 0, "alerts": [], "recommendations": []}
    if raw:
        try:
            parsed = json.loads(raw if raw.startswith("{") else raw[raw.index("{"):])
            if isinstance(parsed, dict):
                result.update(parsed)
        except (json.JSONDecodeError, ValueError):
            result["recommendations"] = [raw[:300]]
    result["safety_disclaimer"] = SAFETY_DISCLAIMER
    return result


def _resources(body: Dict[str, Any]) -> Dict[str, Any]:
    """Health education resources for a given diagnosis or symptoms."""
    diagnosis = (body.get("diagnosis") or "").strip()
    symptoms = body.get("symptoms") or []
    prompt_parts = []
    if diagnosis:
        prompt_parts.append(f"Diagnosis: {diagnosis}")
    if symptoms:
        prompt_parts.append(f"Symptoms: {', '.join(symptoms) if isinstance(symptoms, list) else symptoms}")
    prompt = "\n".join(prompt_parts) or "General health education"
    system = (
        "You are a patient education specialist. Provide health guides and resources for the given condition. "
        "Format as JSON: {\"guides\": [{\"title\": \"...\", \"content\": \"...\", \"type\": \"guide|plan|education\"}], "
        "\"recovery_plan\": \"...\"}. Respond with ONLY valid JSON."
    )
    raw = _bedrock_converse(prompt, system, max_tokens=700)
    result = {"guides": [], "recovery_plan": ""}
    if raw:
        try:
            parsed = json.loads(raw if raw.startswith("{") else raw[raw.index("{"):])
            if isinstance(parsed, dict):
                result.update(parsed)
        except (json.JSONDecodeError, ValueError):
            result["guides"] = [{"title": "Health Guide", "content": raw[:500], "type": "guide"}]
    result["safety_disclaimer"] = SAFETY_DISCLAIMER
    return result


def handler(event: dict, context: object) -> dict:
    """Handle POST /api/ai/* or POST /api/v1/ai/*. Routes by path suffix."""
    try:
        method = (event.get("httpMethod") or "POST").upper()
        if method != "POST":
            return json_response(405, {"error": "Method not allowed"}, event=event)
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]
        # Support both /api/ai/summarize (proxy=ai/summarize) and /api/v1/ai/summarize (proxy=v1/ai/summarize)
        action = ""
        if len(parts) >= 2 and parts[0].lower() == "ai":
            action = (parts[1] or "").lower()
        elif len(parts) >= 3 and parts[0].lower() == "v1" and parts[1].lower() == "ai":
            action = (parts[2] or "").lower()
        if not action:
            return json_response(404, {"error": "Not found"}, event=event)
        body = parse_body_json(event)
        actions = {
            "summarize": _summarize,
            "entities": _entities,
            "surgery-support": _surgery_support,
            "translate": _translate,
            "prescription": _prescription,
            "adherence": _adherence,
            "engagement": _engagement,
            "resources": _resources,
        }
        fn = actions.get(action)
        if fn:
            return json_response(200, fn(body), event=event)
        return json_response(404, {"error": "Unknown AI action", "allowed": list(actions.keys())}, event=event)
    except Exception as e:
        logger.exception("AI handler error: %s", e)
        return json_response(500, {"error": "Internal server error", "safety_disclaimer": SAFETY_DISCLAIMER}, event=event)
