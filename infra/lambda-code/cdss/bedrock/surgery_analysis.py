"""
Surgery checklist/requirements helper.
"""

from __future__ import annotations

import json

from cdss.bedrock.chat import invoke_chat


def get_surgery_checklist_analysis(
    surgery_type: str,
    patient_conditions: str,
    existing_checklist: list[str] | None = None,
) -> dict | None:
    prompt = (
        "You are a surgical planning assistant.\n"
        "Given the surgery type and patient conditions, propose an updated pre-op checklist.\n"
        "Return JSON with keys: checklist_items (array of strings), pre_op_status (string), "
        "risk_factors (array of strings), requires_senior_review (boolean).\n\n"
        f"Surgery type: {surgery_type}\n"
        f"Patient conditions: {patient_conditions}\n"
        f"Existing checklist: {(existing_checklist or [])[:30]}\n"
    )
    result = invoke_chat(prompt)
    text = (result.reply or "").strip()
    if not text:
        return None

    # Bedrock responses may wrap JSON in markdown fences.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Try parse JSON; if model returns prose, ignore.
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None
