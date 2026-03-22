"""
Visit summary and medical entity extraction helpers.

Phase 1–2: best-effort extraction; safe fallbacks if Bedrock unavailable.
"""

from __future__ import annotations

import json

from cdss.bedrock.chat import invoke_chat


def generate_visit_summary(transcript_text: str, patient_context: str = "") -> str | None:
    prompt = (
        "You are a clinical documentation assistant.\n"
        "Summarize the visit for the patient's record. Keep it factual and concise.\n"
        "Do not invent data.\n\n"
        f"Patient context: {patient_context}\n\n"
        f"Transcript/notes:\n{(transcript_text or '')[:6000]}"
    )
    res = invoke_chat(prompt)
    return res.reply if res.reply else None


def extract_medical_entities(transcript_text: str) -> dict | None:
    prompt = (
        "Extract medical entities from the transcript.\n"
        "Return JSON with keys: symptoms, diagnoses, medications, instructions, follow_up_actions.\n"
        "Each value should be an array of strings.\n\n"
        f"Transcript:\n{(transcript_text or '')[:6000]}"
    )
    res = invoke_chat(prompt)
    text = (res.reply or "").strip()
    if not text:
        return None

    # Bedrock responses may wrap JSON in markdown code fences.
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence like ``` or ```json
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Drop closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {
        "symptoms": [],
        "diagnoses": [],
        "medications": [],
        "instructions": [],
        "follow_up_actions": [],
    }
