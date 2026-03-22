"""
Patient summary helper.

Phase 1–2: generate a short clinician-facing summary from Patient + recent visits.
"""

from __future__ import annotations

from typing import Any

from cdss.bedrock.chat import invoke_chat_with_context


def get_patient_summary(patient: Any, visits: list[Any]) -> str | None:
    data = {
        "patient": {
            # Intentionally exclude direct identifiers (id, name) from model context.
            "gender": getattr(patient, "gender", None),
            "conditions": getattr(patient, "conditions", None),
            "allergies": getattr(patient, "allergies", None),
            "vitals": getattr(patient, "vitals", None),
            "severity": getattr(patient, "severity", None),
            "status": getattr(patient, "status", None),
            "surgery_readiness": getattr(patient, "surgery_readiness", None),
        },
        "recent_visits": [
            {
                "id": getattr(v, "id", None),
                "date": getattr(v, "visit_date", None) and getattr(v, "visit_date").isoformat(),
                "doctor_id": getattr(v, "doctor_id", None),
                "notes": (getattr(v, "notes", None) or "")[:1200],
                "summary": (getattr(v, "summary", None) or "")[:1200],
            }
            for v in (visits or [])[:5]
        ],
    }
    result = invoke_chat_with_context(
        "Provide a concise clinician-facing summary (problems, meds mentioned, red flags, next steps). "
        "Do not include any patient-identifying details.",
        "Patient record and recent visits",
        data,
    )
    return result.reply if result and result.reply else None
