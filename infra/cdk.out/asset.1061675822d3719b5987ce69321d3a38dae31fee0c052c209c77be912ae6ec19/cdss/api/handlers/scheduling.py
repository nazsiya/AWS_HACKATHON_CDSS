"""
Scheduling agent handler – schedule slots from Aurora (Phase 5–6).

GET /api/v1/schedule: slots linked to surgeries and OTs; return { schedule: [...] }.
POST /api/v1/schedule: book a slot (ot_id, slot_date, slot_time, surgery_id).
POST /api/v1/schedule/find-replacement: body doctor_id, surgery_id, date → replacement options (staff from Aurora).
GET /api/v1/schedule/utilisation: OT utilisation metrics for admin.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from cdss.api.handlers.common import json_response, parse_body_json
from cdss.db.models import Patient, Resource, ScheduleSlot, Surgery
from cdss.db.session import get_session
from cdss.services.notifications import send_doctor_escalation, send_surgery_alert

logger = logging.getLogger(__name__)


def _serialize_date(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _slot_to_item(slot: ScheduleSlot, patient_name: str | None, surgery_type: str | None = None) -> dict:
    """One schedule slot for frontend."""
    return {
        "id": slot.id,
        "ot": slot.ot_id,
        "date": _serialize_date(slot.slot_date),
        "time": slot.slot_time,
        "surgeryId": slot.surgery_id,
        "patient": patient_name or "—",
        "type": surgery_type or "Surgery",
        "status": slot.status,
    }


def _list_schedule() -> dict:
    """Return schedule from Aurora (slots with surgery and patient name)."""
    with get_session() as session:
        stmt = (
            select(ScheduleSlot, Patient.name, Surgery.type)
            .outerjoin(Surgery, ScheduleSlot.surgery_id == Surgery.id)
            .outerjoin(Patient, Surgery.patient_id == Patient.id)
            .order_by(ScheduleSlot.slot_date, ScheduleSlot.slot_time)
        )
        rows = session.execute(stmt).all()
        schedule = [_slot_to_item(slot, pname, s_type) for slot, pname, s_type in rows]
        return json_response(200, {"schedule": schedule})


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


def _post_schedule(event: dict) -> dict:
    """POST /api/v1/schedule – book a slot. Body: ot_id, slot_date, slot_time, surgery_id (optional)."""
    body = parse_body_json(event)
    ot_id = (body.get("ot_id") or body.get("otId") or "").strip()
    slot_date = _parse_date(body.get("slot_date") or body.get("slotDate"))
    slot_time = (body.get("slot_time") or body.get("slotTime") or "").strip()
    surgery_id = (body.get("surgery_id") or body.get("surgeryId") or "").strip() or None
    if not ot_id or not slot_date or not slot_time:
        return json_response(400, {"error": "ot_id, slot_date, and slot_time are required"})

    with get_session() as session:
        stmt = (
            select(ScheduleSlot)
            .where(
                ScheduleSlot.ot_id == ot_id,
                ScheduleSlot.slot_date == slot_date,
                ScheduleSlot.slot_time == slot_time,
            )
        )
        existing = session.scalar(stmt)
        if existing and existing.status == "booked":
            # Notify about conflict via SNS
            send_doctor_escalation(
                doctor_id="scheduler",
                alert_type="surgery_conflict",
                context={
                    "ot_id": ot_id,
                    "slot_date": str(slot_date),
                    "slot_time": slot_time,
                    "existing_slot_id": existing.id,
                    "reason": "Double-booking attempted",
                },
            )
            return json_response(409, {"error": "Slot already booked", "slot_id": existing.id})
        if existing:
            existing.surgery_id = surgery_id
            existing.status = "booked"
            session.flush()
            out = _slot_to_item(existing, None)
            return json_response(200, {"schedule": [out], "message": "Slot updated"})
        slot = ScheduleSlot(
            ot_id=ot_id,
            slot_date=slot_date,
            slot_time=slot_time,
            surgery_id=surgery_id,
            status="booked",
            created_at=datetime.now(timezone.utc),
        )
        session.add(slot)
        session.flush()
        out = _slot_to_item(slot, None)
        return json_response(201, {"schedule": [out], "message": "Slot booked"})


def _post_find_replacement(event: dict) -> dict:
    """POST /api/v1/schedule/find-replacement – find replacement doctors/staff. Body: doctor_id, surgery_id, date."""
    body = parse_body_json(event)
    doctor_id = (body.get("doctor_id") or body.get("doctorId") or "").strip()
    surgery_id = (body.get("surgery_id") or body.get("surgeryId") or "").strip()
    slot_date = _parse_date(body.get("date") or body.get("slot_date"))
    if not doctor_id and not surgery_id:
        return json_response(400, {"error": "doctor_id or surgery_id required"})

    with get_session() as session:
        # Potential replacements: staff resources that are available (or any staff if no specialty match)
        stmt = select(Resource).where(Resource.type == "staff").order_by(Resource.id)
        staff = list(session.scalars(stmt).all())
        options = []
        for s in staff:
            if s.id == doctor_id:
                continue
            avail = s.availability or {}
            options.append({
                "id": s.id,
                "name": s.name,
                "specialty": avail.get("specialty", "—"),
                "status": s.status,
                "availability": avail,
            })
        return json_response(200, {
            "replacements": options[:20],
            "surgery_id": surgery_id or None,
            "date": slot_date.isoformat() if slot_date else None,
            "message": "Use Notify to send replacement request to escalation topic.",
        })


def _post_notify_replacement(event: dict) -> dict:
    """POST /api/v1/schedule/notify-replacement – publish replacement request via notification service."""
    body = parse_body_json(event)
    surgery_id = (body.get("surgery_id") or body.get("surgeryId") or "").strip()
    doctor_id = (body.get("doctor_id") or body.get("doctorId") or "").strip()
    if not surgery_id or not doctor_id:
        return json_response(400, {"error": "surgery_id and doctor_id required"})

    result = send_doctor_escalation(
        doctor_id=doctor_id,
        alert_type="replacement_requested",
        context={
            "surgery_id": surgery_id,
            "original_doctor": doctor_id,
            "reason": "Replacement requested – please assign from available staff.",
        },
    )
    if result.get("success"):
        return json_response(200, {
            "notified": True,
            "surgery_id": surgery_id,
            "trace_id": result.get("trace_id"),
            "message": "Replacement request sent to doctor escalations.",
        })
    return json_response(503, {
        "error": "Notification delivery failed",
        "reason": result.get("reason", "SNS topic not configured"),
    })


def _get_utilisation() -> dict:
    """GET /api/v1/schedule/utilisation – OT utilisation metrics (Phase 6)."""
    from sqlalchemy import case

    with get_session() as session:
        stmt = (
            select(
                ScheduleSlot.ot_id,
                ScheduleSlot.slot_date,
                func.count(ScheduleSlot.id).label("total"),
                func.sum(case((ScheduleSlot.status == "booked", 1), else_=0)).label("booked"),
            )
            .where(ScheduleSlot.ot_id.isnot(None), ScheduleSlot.slot_date.isnot(None))
            .group_by(ScheduleSlot.ot_id, ScheduleSlot.slot_date)
            .order_by(ScheduleSlot.slot_date.desc(), ScheduleSlot.ot_id)
        )
        rows = session.execute(stmt).all()
        utilisation = []
        for r in rows:
            total = r.total or 0
            booked = r.booked or 0
            pct = round(100.0 * booked / total, 1) if total else 0
            utilisation.append({
                "ot_id": r.ot_id,
                "date": str(r.slot_date),
                "slots_total": total,
                "slots_booked": booked,
                "utilisation_pct": pct,
            })
        return json_response(200, {"utilisation": utilisation})


def handler(event: dict, context: object) -> dict:
    """Handle GET/POST /api/v1/schedule, POST find-replacement, GET utilisation."""
    try:
        method = (event.get("httpMethod") or "GET").upper()
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]
        if len(parts) < 2 or parts[0].lower() != "v1" or parts[1].lower() != "schedule":
            return json_response(404, {"error": "Not found"})

        sub = (parts[2] or "").lower() if len(parts) > 2 else ""
        if sub == "find-replacement" and method == "POST":
            return _post_find_replacement(event)
        if sub == "notify-replacement" and method == "POST":
            return _post_notify_replacement(event)
        if sub == "utilisation" and method == "GET":
            return _get_utilisation()

        if method == "GET":
            return _list_schedule()
        if method == "POST":
            return _post_schedule(event)
        return json_response(405, {"error": "Method not allowed"})
    except Exception as e:
        logger.error(
            "Scheduling handler error",
            extra={"error": str(e), "handler": "scheduling"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
