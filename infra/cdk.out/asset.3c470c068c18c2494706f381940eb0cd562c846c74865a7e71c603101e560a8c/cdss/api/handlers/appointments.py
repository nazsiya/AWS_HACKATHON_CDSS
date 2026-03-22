"""
Appointments handler – list and create appointments from Aurora.

GET  /api/v1/appointments           → list appointments (visits joined with patient + doctor)
POST /api/v1/appointments           → create a new appointment (visit)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict

from cdss.api.handlers.common import cors_headers, json_response, parse_body_json, query_int
from cdss.db.models import Visit, Patient, Doctor
from cdss.db.session import get_session

logger = logging.getLogger(__name__)


def _serialize_dt(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.isoformat()
    if isinstance(d, date):
        return d.isoformat()
    return str(d)


def _visit_to_appointment(visit: Visit, patient_name: str | None, doctor_name: str | None) -> dict:
    visit_dt = visit.visit_date if hasattr(visit, "visit_date") else visit.created_at
    date_str = ""
    time_str = ""
    if visit_dt:
        if isinstance(visit_dt, datetime):
            date_str = visit_dt.strftime("%Y-%m-%d")
            time_str = visit_dt.strftime("%H:%M")
        elif isinstance(visit_dt, date):
            date_str = visit_dt.isoformat()
            time_str = "09:00"

    # Determine type from notes or default
    notes = getattr(visit, "notes", "") or ""
    visit_type = "Consultation"
    if "follow" in notes.lower():
        visit_type = "Follow-up"
    elif "lab" in notes.lower():
        visit_type = "Lab Review"
    elif "pre-op" in notes.lower():
        visit_type = "Pre-op Check"

    return {
        "id": visit.id if hasattr(visit, "id") else None,
        "date": date_str,
        "time": time_str,
        "patient": patient_name or "Unknown",
        "patient_id": visit.patient_id,
        "doctor": doctor_name or "Unknown",
        "doctor_id": visit.doctor_id,
        "type": visit_type,
        "status": "Scheduled",
        "notes": notes,
    }


def _list_appointments(event: dict) -> dict:
    """GET /api/v1/appointments — list all appointments from visits table."""
    try:
        from sqlalchemy import select

        with get_session() as session:
            stmt = (
                select(Visit, Patient.name, Doctor.full_name)
                .outerjoin(Patient, Visit.patient_id == Patient.id)
                .outerjoin(Doctor, Visit.doctor_id == Doctor.doctor_id)
                .order_by(Visit.visit_date.desc().nullslast())
                .limit(100)
            )
            rows = session.execute(stmt).all()
            items = [_visit_to_appointment(v, pname, dname) for v, pname, dname in rows]
            return json_response(200, {"appointments": items}, event=event)
    except Exception as e:
        logger.warning("Appointments list failed: %s", e, exc_info=True)
        return json_response(200, {"appointments": [], "_error": str(e)}, event=event)


def _create_appointment(event: dict) -> dict:
    """POST /api/v1/appointments — create a new visit/appointment."""
    try:
        body = parse_body_json(event)
        patient_id = (body.get("patient_id") or "").strip()
        doctor_id = (body.get("doctor_id") or "").strip()
        notes = (body.get("notes") or "").strip()
        visit_date_str = (body.get("date") or body.get("visit_date") or "").strip()

        if not patient_id:
            return json_response(400, {"error": "patient_id is required"}, event=event)

        visit_date = None
        if visit_date_str:
            try:
                visit_date = datetime.fromisoformat(visit_date_str).date()
            except (ValueError, TypeError):
                try:
                    visit_date = datetime.strptime(visit_date_str[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass

        with get_session() as session:
            visit = Visit(
                patient_id=patient_id,
                doctor_id=doctor_id or None,
                visit_date=visit_date or date.today(),
                notes=notes or None,
                created_at=datetime.now(timezone.utc),
            )
            session.add(visit)
            session.flush()
            return json_response(
                201,
                {"id": visit.id, "patient_id": patient_id, "status": "created"},
                event=event,
            )
    except Exception as e:
        logger.warning("Create appointment failed: %s", e, exc_info=True)
        return json_response(500, {"error": str(e)}, event=event)


def handler(event: dict, context: object) -> dict:
    """Handle GET/POST /api/v1/appointments."""
    method = (event.get("httpMethod") or "GET").upper()
    if method == "GET":
        return _list_appointments(event)
    if method == "POST":
        return _create_appointment(event)
    return json_response(405, {"error": "Method not allowed"}, event=event)
