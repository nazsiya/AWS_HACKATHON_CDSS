"""
Surgery agent handler – surgery list, detail, create, update, and analyse from Aurora.

GET /api/v1/surgeries: list from Aurora with patient name.
GET /api/v1/surgeries/:id: detail with checklist and requiredInstruments.
POST /api/v1/surgeries: create surgery.
PUT /api/v1/surgeries/:id: update surgery (including checklist).
POST /api/v1/surgeries/:id/analyse: request AI checklist/requirements (CDSS schemas).
Per bedrock-agents: validated outputs; no raw EMR writes.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone

from sqlalchemy import select

from cdss.api.handlers.common import json_response, parse_body_json
from cdss.db.models import Patient, Surgery
from cdss.db.session import get_session

logger = logging.getLogger(__name__)

# Default checklist items when not stored in DB (per plan: procedural checklist).
DEFAULT_CHECKLIST = [
    {"id": 1, "text": "Confirm patient identity, site, and procedure", "completed": False},
    {"id": 2, "text": "Marking of surgical site complete", "completed": False},
    {"id": 3, "text": "Anesthesia safety check complete", "completed": False},
    {"id": 4, "text": "Pulse oximeter on patient and functioning", "completed": False},
    {"id": 5, "text": "Antibiotic prophylaxis administered", "completed": False},
    {"id": 6, "text": "Confirmation of sterility indicators", "completed": False},
]


def _serialize_date(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _surgery_list_item(surgery: Surgery, patient_name: str | None) -> dict:
    """One surgery for list view (frontend shape)."""
    duration = surgery.duration_minutes
    duration_str = f"{duration} min" if duration else None
    return {
        "id": surgery.id,
        "patient": patient_name or "Unknown",
        "type": surgery.type,
        "complexity": _complexity_from_requirements(surgery.requirements),
        "estimatedDuration": duration_str,
        "ot": surgery.ot_id or "—",
        "date": _serialize_date(surgery.scheduled_date),
        "time": surgery.scheduled_time or "—",
        "status": surgery.status,
        "surgeon": surgery.surgeon_id or "—",
    }


def _complexity_from_requirements(requirements: dict | None) -> str:
    """Derive complexity from requirements JSON or default."""
    if requirements and isinstance(requirements, dict):
        return requirements.get("complexity", "Moderate")
    return "Moderate"


def _required_instruments(surgery: Surgery) -> list[str]:
    """Required instruments from requirements JSON or default set."""
    if surgery.requirements and isinstance(surgery.requirements, dict):
        instr = surgery.requirements.get("instruments")
        if isinstance(instr, list):
            return instr
    return ["Standard surgical set", "Electrocautery", "Suction", "Suture kit"]


def _checklist_from_raw(raw: list | dict | None) -> list:
    """Normalize checklist to frontend shape [{ id, text, completed }]."""
    if isinstance(raw, list):
        return [
            {
                "id": item.get("id", i + 1),
                "text": item.get("text", str(item)),
                "completed": bool(item.get("completed", False)),
            }
            for i, item in enumerate(raw)
        ]
    if isinstance(raw, dict) and "items" in raw:
        return _checklist_from_raw(raw["items"])
    return list(DEFAULT_CHECKLIST)


def _analyse_surgery_sync(surgery_id: str) -> dict | None:
    """
    Generate checklist and requirements for a surgery (sync, optional Bedrock).
    Returns CDSS-aligned structure. Never raises: on DB/Bedrock failure returns default checklist.
    """
    default_result = {
        "surgery_id": surgery_id,
        "pre_op_status": "pending",
        "checklist": list(DEFAULT_CHECKLIST),
        "checklist_flags": [c["text"] for c in DEFAULT_CHECKLIST],
        "requiredInstruments": ["Standard surgical set", "Electrocautery", "Suction", "Suture kit"],
        "risk_factors": [],
        "requires_senior_review": False,
        "safety_disclaimer": "AI is for support only. Clinical decisions require qualified judgment.",
    }
    try:
        with get_session() as session:
            stmt = (
                select(Surgery, Patient)
                .join(Patient, Surgery.patient_id == Patient.id)
                .where(Surgery.id == surgery_id)
            )
            row = session.execute(stmt).first()
            if row is None:
                return None
            surgery, patient = row
    except Exception as e:
        logger.warning("Surgery analyse: database unavailable for %s: %s", surgery_id, e)
        return default_result

    conditions = getattr(patient, "conditions", None) or []
    conditions_str = ", ".join(conditions) if isinstance(conditions, list) else str(conditions)
    risk_factors = list(conditions) if isinstance(conditions, list) else [conditions_str] if conditions_str else []

    checklist = _checklist_from_raw(surgery.checklist)
    required_instruments = _required_instruments(surgery)
    pre_op_status = "pending"
    requires_senior_review = False

    try:
        from cdss.bedrock.surgery_analysis import get_surgery_checklist_analysis

        result = get_surgery_checklist_analysis(
            surgery_type=surgery.type,
            patient_conditions=conditions_str or "none",
            existing_checklist=[c["text"] for c in checklist],
        )
        if result:
            if result.get("checklist_items"):
                checklist = [
                    {"id": i + 1, "text": t, "completed": False}
                    for i, t in enumerate(result["checklist_items"])
                ]
            pre_op_status = result.get("pre_op_status") or pre_op_status
            requires_senior_review = result.get("requires_senior_review", requires_senior_review)
            if result.get("risk_factors"):
                risk_factors = result["risk_factors"]
    except Exception as e:
        logger.debug("Surgery analysis Bedrock skip: %s", e)

    return {
        "surgery_id": surgery_id,
        "pre_op_status": pre_op_status,
        "checklist": checklist,
        "checklist_flags": [c["text"] for c in checklist if not c.get("completed")],
        "requiredInstruments": required_instruments,
        "risk_factors": risk_factors,
        "requires_senior_review": requires_senior_review,
        "safety_disclaimer": "AI is for support only. Clinical decisions require qualified judgment.",
    }


def _list_surgeries() -> dict:
    """List surgeries from Aurora with patient name."""
    with get_session() as session:
        stmt = (
            select(Surgery, Patient.name)
            .outerjoin(Patient, Surgery.patient_id == Patient.id)
            .order_by(Surgery.scheduled_date.desc(), Surgery.scheduled_time)
        )
        rows = session.execute(stmt).all()
        list_data = [
            _surgery_list_item(surgery, pname) for surgery, pname in rows
        ]
        return json_response(200, {"surgeries": list_data})


def _get_surgery(surgery_id: str) -> dict:
    """Single surgery with checklist and requiredInstruments."""
    with get_session() as session:
        stmt = (
            select(Surgery, Patient.name)
            .outerjoin(Patient, Surgery.patient_id == Patient.id)
            .where(Surgery.id == surgery_id)
        )
        row = session.execute(stmt).first()
        if row is None:
            return json_response(404, {"error": "Surgery not found"})
        surgery, patient_name = row
        out = _surgery_list_item(surgery, patient_name)
        out["checklist"] = _checklist_from_raw(surgery.checklist)
        out["requiredInstruments"] = _required_instruments(surgery)
        return json_response(200, out)


def _next_surgery_id(session) -> str:
    """Generate next surgery id (e.g. SRG-1001). Uses max numeric suffix from existing ids."""
    rows = session.execute(select(Surgery.id)).scalars().all()
    max_num = 0
    for sid in rows:
        m = re.match(r"SRG-(\d+)", (sid or "").upper())
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"SRG-{max_num + 1}"


def _parse_date(value: str | None) -> date | None:
    """Parse ISO date string to date. Returns None if invalid."""
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _post_surgeries(event: dict) -> dict:
    """POST /api/v1/surgeries – create surgery. Body: patient_id, type, scheduled_date, ..."""
    body = parse_body_json(event)
    patient_id = (body.get("patient_id") or body.get("patientId") or "").strip()
    surgery_type = (body.get("type") or body.get("surgery_type") or "").strip()
    if not patient_id or not surgery_type:
        return json_response(400, {"error": "patient_id and type are required"})

    with get_session() as session:
        stmt = select(Patient).where(Patient.id == patient_id)
        if session.scalar(stmt) is None:
            return json_response(404, {"error": "Patient not found"})

        surgery_id = _next_surgery_id(session)
        now = datetime.now(timezone.utc)
        surgery = Surgery(
            id=surgery_id,
            patient_id=patient_id,
            type=surgery_type,
            surgeon_id=(body.get("surgeon_id") or body.get("surgeonId") or "").strip() or None,
            ot_id=(body.get("ot_id") or body.get("otId") or "").strip() or None,
            scheduled_date=_parse_date(body.get("scheduled_date") or body.get("scheduledDate")),
            scheduled_time=(body.get("scheduled_time") or body.get("scheduledTime") or "").strip() or None,
            duration_minutes=body.get("duration_minutes") or body.get("durationMinutes"),
            status=(body.get("status") or "scheduled").strip(),
            checklist=None,
            requirements=body.get("requirements"),
            created_at=now,
            updated_at=now,
        )
        session.add(surgery)
        session.flush()
        out = _surgery_list_item(surgery, None)
        out["checklist"] = _checklist_from_raw(surgery.checklist)
        out["requiredInstruments"] = _required_instruments(surgery)
        return json_response(201, out)


def _put_surgery(event: dict, surgery_id: str) -> dict:
    """PUT /api/v1/surgeries/:id – update surgery (including checklist)."""
    body = parse_body_json(event)
    with get_session() as session:
        stmt = select(Surgery).where(Surgery.id == surgery_id)
        surgery = session.scalar(stmt)
        if surgery is None:
            return json_response(404, {"error": "Surgery not found"})

        if "type" in body and body["type"] is not None:
            surgery.type = (str(body["type"]) or "").strip() or surgery.type
        if "surgeon_id" in body or "surgeonId" in body:
            surgery.surgeon_id = (str(body.get("surgeon_id") or body.get("surgeonId")) or "").strip() or None
        if "ot_id" in body or "otId" in body:
            surgery.ot_id = (str(body.get("ot_id") or body.get("otId")) or "").strip() or None
        if "scheduled_date" in body or "scheduledDate" in body:
            surgery.scheduled_date = _parse_date(body.get("scheduled_date") or body.get("scheduledDate"))
        if "scheduled_time" in body or "scheduledTime" in body:
            surgery.scheduled_time = (str(body.get("scheduled_time") or body.get("scheduledTime")) or "").strip() or None
        if "duration_minutes" in body or "durationMinutes" in body:
            surgery.duration_minutes = body.get("duration_minutes") or body.get("durationMinutes")
        if "status" in body and body["status"] is not None:
            surgery.status = (str(body["status"]) or "").strip() or surgery.status
        if "requirements" in body:
            surgery.requirements = body["requirements"]
        if "checklist" in body and isinstance(body["checklist"], list):
            surgery.checklist = body["checklist"]

        surgery.updated_at = datetime.now(timezone.utc)
        session.flush()
        stmt_p = select(Patient.name).where(Patient.id == surgery.patient_id)
        patient_name = session.scalar(stmt_p)
        out = _surgery_list_item(surgery, patient_name)
        out["checklist"] = _checklist_from_raw(surgery.checklist)
        out["requiredInstruments"] = _required_instruments(surgery)
        return json_response(200, out)


def _post_analyse(surgery_id: str) -> dict:
    """POST /api/v1/surgeries/:id/analyse – AI checklist/requirements (CDSS schemas)."""
    result = _analyse_surgery_sync(surgery_id)
    if result is None:
        return json_response(404, {"error": "Surgery not found"})
    return json_response(200, result)


def handler(event: dict, context: object) -> dict:
    """Handle GET/POST /api/v1/surgeries, GET/PUT /api/v1/surgeries/:id, POST /api/v1/surgeries/:id/analyse."""
    try:
        method = (event.get("httpMethod") or "GET").upper()
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]
        if len(parts) < 2 or parts[0].lower() != "v1" or parts[1].lower() != "surgeries":
            return json_response(404, {"error": "Not found"})

        surgery_id = parts[2] if len(parts) > 2 else None
        is_analyse = len(parts) >= 4 and (parts[3] or "").lower() == "analyse"

        if surgery_id:
            if is_analyse and method == "POST":
                return _post_analyse(surgery_id)
            if method == "GET":
                return _get_surgery(surgery_id)
            if method == "PUT":
                return _put_surgery(event, surgery_id)
            return json_response(405, {"error": "Method not allowed"})

        if method == "GET":
            return _list_surgeries()
        if method == "POST":
            return _post_surgeries(event)
        return json_response(405, {"error": "Method not allowed"})
    except Exception as e:
        logger.error(
            "Surgery handler error",
            extra={"error": str(e), "handler": "surgery"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
