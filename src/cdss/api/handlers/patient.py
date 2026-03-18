"""
Patient agent handler – patient list, detail, create, and update from Aurora.

GET /api/v1/patients: list from Aurora (id, name, lastVisit, nextAppointment).
GET /api/v1/patients/:id: full patient from Aurora; optional ABDM stub and optional Bedrock summary.
POST /api/v1/patients: createPatient – create patient in Aurora.
PUT /api/v1/patients/:id: updateRecord – update patient in Aurora.
Per project-conventions: no PHI in logs; audit via router.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone

from cdss.api.handlers.common import json_response, parse_body_json
from cdss.db.session import get_session
from cdss.mcp.adapter import get_abdm_record
from cdss.services.alerts import check_vital_thresholds

logger = logging.getLogger(__name__)


def _serialize_date(d: date | datetime | None) -> str | None:
    """ISO date/datetime for JSON; no PHI."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.isoformat()
    return d.isoformat()


def _age_from_dob(dob) -> int | None:
    """Compute age in years from date of birth; None if dob is None."""
    if dob is None:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _patient_list_item(patient) -> dict:
    """Single patient for list view; includes frontend-expected fields (Patients.jsx, Medications.jsx)."""
    return {
        "id": patient.id,
        "name": patient.name,
        "age": _age_from_dob(patient.date_of_birth),
        "gender": patient.gender or "",
        "bloodGroup": getattr(patient, "blood_group", None) or "",
        "ward": getattr(patient, "ward", None) or "",
        "severity": getattr(patient, "severity", None) or "",
        "status": getattr(patient, "status", None) or "",
        "vitals": getattr(patient, "vitals", None) or {},
        "conditions": [c.condition_name if hasattr(c, 'condition_name') else str(c) for c in (patient.conditions or [])],
        "lastVisit": _serialize_date(patient.last_visit),
        "nextAppointment": None,
    }


def _visit_to_consultation(visit) -> dict:
    """Format Visit as consultationHistory item (PatientConsultation.jsx)."""
    return {
        "id": visit.id,
        "date": visit.visit_date.isoformat() if visit.visit_date else None,
        "doctor": visit.doctor_id,
        "notes": visit.notes or "",
        "aiSummary": visit.summary or "",
        "prescriptions": [],
    }


def _patient_detail(patient, include_abdm: bool = False, ai_summary: str | None = None, consultation_history: list | None = None) -> dict:
    """Full patient object for frontend (camelCase); includes consultationHistory when provided."""
    out = {
        "id": patient.id,
        "name": patient.name,
        "dateOfBirth": _serialize_date(patient.date_of_birth),
        "age": _age_from_dob(patient.date_of_birth),
        "gender": patient.gender or "",
        "bloodGroup": getattr(patient, "blood_group", None) or "",
        "ward": getattr(patient, "ward", None) or "",
        "severity": getattr(patient, "severity", None) or "",
        "status": getattr(patient, "status", None) or "",
        "vitals": getattr(patient, "vitals", None) or {},
        "conditions": [c.condition_name if hasattr(c, 'condition_name') else str(c) for c in (patient.conditions or [])],
        "medications": [],
        "lastVisit": _serialize_date(patient.last_visit),
        "nextAppointment": None,
        "surgeryReadiness": getattr(patient, "surgery_readiness", None) or {},
    }
    if consultation_history is not None:
        out["consultationHistory"] = consultation_history
    if include_abdm:
        abdm = get_abdm_record(patient.id)
        if not abdm.get("error"):
            out["abdm"] = abdm
    if ai_summary is not None:
        out["aiSummary"] = ai_summary
    return out


def _generate_patient_summary(patient, visits: list | None = None) -> str | None:
    """Optional Bedrock summary for patient (doctor-in-the-loop; validated). Returns None if Bedrock unavailable."""
    try:
        from cdss.bedrock.patient_summary import get_patient_summary

        return get_patient_summary(patient, visits or [])
    except Exception as e:
        logger.debug("Patient summary skipped", extra={"error": str(e)})
        return None


def _list_patients() -> dict:
    """Return patient list from Aurora."""
    with get_session() as session:
        from sqlalchemy import select
        from cdss.db.models import Patient

        stmt = select(Patient).order_by(Patient.updated_at.desc())
        rows = session.scalars(stmt).all()
        list_view = [_patient_list_item(p) for p in rows]
        return json_response(200, {"patients": list_view})


def _get_patient(patient_id: str) -> dict:
    """Return single patient by id with optional ABDM, Bedrock summary, and consultationHistory from Visit."""
    with get_session() as session:
        from sqlalchemy import select
        from cdss.db.models import Patient, Visit

        stmt = select(Patient).where(Patient.id == patient_id)
        patient = session.scalar(stmt)
        if patient is None:
            return json_response(404, {"error": "Patient not found"})
        visits_stmt = select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc(), Visit.created_at.desc())
        visits = list(session.scalars(visits_stmt).all())
        ai_summary = _generate_patient_summary(patient, visits)
        consultation_history = [_visit_to_consultation(v) for v in visits]
        out = _patient_detail(patient, include_abdm=True, ai_summary=ai_summary, consultation_history=consultation_history)
        return json_response(200, out)


def _next_patient_id(session) -> str:
    """Generate next patient id (e.g. PT-1001). Uses max numeric suffix from existing ids."""
    from sqlalchemy import select
    from cdss.db.models import Patient

    rows = session.execute(select(Patient.id)).scalars().all()
    max_num = 0
    for pid in rows:
        m = re.match(r"PT-(\d+)", (pid or "").upper())
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"PT-{max_num + 1}"


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


def _post_patients(event: dict) -> dict:
    """POST /api/v1/patients – createPatient. Body: name (required), dateOfBirth, gender, language, conditions, allergies, abha_id."""
    body = parse_body_json(event)
    name = (body.get("name") or "").strip()
    if not name:
        return json_response(400, {"error": "name is required"})

    with get_session() as session:
        from cdss.db.models import Patient

        # Enforce unique abha_id — return 409 if duplicate
        abha_id_val = (body.get("abha_id") or body.get("abhaId") or "").strip() or None
        if abha_id_val:
            existing = session.query(Patient).filter(Patient.abha_id == abha_id_val).first()
            if existing:
                return json_response(409, {
                    "error": f"Patient with abha_id '{abha_id_val}' already exists",
                    "existing_patient_id": existing.id,
                })

        patient_id = _next_patient_id(session)
        now = datetime.now(timezone.utc)
        dob = _parse_date(body.get("dateOfBirth") or body.get("date_of_birth"))
        conditions = body.get("conditions")
        if conditions is not None and not isinstance(conditions, list):
            conditions = [conditions] if conditions else []
        allergies = body.get("allergies")
        if allergies is not None and not isinstance(allergies, list):
            allergies = [allergies] if allergies else []

        patient = Patient(
            id=patient_id,
            name=name,
            date_of_birth=dob,
            gender=(body.get("gender") or "").strip() or None,
            language=(body.get("language") or "").strip() or None,
            abha_id=(body.get("abha_id") or body.get("abhaId") or "").strip() or None,
            conditions=conditions or None,
            allergies=allergies or None,
            address_json=body.get("address_json") or body.get("address"),
            emergency_contact_json=body.get("emergency_contact_json") or body.get("emergencyContact"),
            created_at=now,
            updated_at=now,
        )
        if "blood_group" in body or "bloodGroup" in body:
            patient.blood_group = (body.get("blood_group") or body.get("bloodGroup") or "").strip() or None
        if "ward" in body:
            patient.ward = (body.get("ward") or "").strip() or None
        if "severity" in body:
            patient.severity = (body.get("severity") or "").strip() or None
        if "status" in body:
            patient.status = (body.get("status") or "").strip() or None
        if "vitals" in body and isinstance(body.get("vitals"), dict):
            patient.vitals = body["vitals"]
            check_vital_thresholds(patient_id, body["vitals"])
        if "surgery_readiness" in body or "surgeryReadiness" in body:
            patient.surgery_readiness = body.get("surgery_readiness") or body.get("surgeryReadiness")
        session.add(patient)
        session.flush()
        out = _patient_detail(patient, include_abdm=False)
        return json_response(201, out)


def _put_patient(event: dict, patient_id: str) -> dict:
    """PUT /api/v1/patients/:id – updateRecord. Body: optional name, dateOfBirth, gender, language, conditions, allergies, etc."""
    body = parse_body_json(event)
    with get_session() as session:
        from sqlalchemy import select
        from cdss.db.models import Patient

        stmt = select(Patient).where(Patient.id == patient_id)
        patient = session.scalar(stmt)
        if patient is None:
            return json_response(404, {"error": "Patient not found"})

        if "name" in body and body["name"] is not None:
            patient.name = (str(body["name"]) or "").strip() or patient.name
        if "dateOfBirth" in body or "date_of_birth" in body:
            dob = _parse_date(body.get("dateOfBirth") or body.get("date_of_birth"))
            if dob is not None:
                patient.date_of_birth = dob
        if "gender" in body:
            patient.gender = (str(body["gender"]) or "").strip() or None
        if "language" in body:
            patient.language = (str(body["language"]) or "").strip() or None
        if "abha_id" in body or "abhaId" in body:
            patient.abha_id = str(body.get("abha_id") or body.get("abhaId") or "").strip() or None
        if "conditions" in body:
            v = body["conditions"]
            patient.conditions = v if isinstance(v, list) else ([v] if v else [])
        if "allergies" in body:
            v = body["allergies"]
            patient.allergies = v if isinstance(v, list) else ([v] if v else [])
        if "address_json" in body or "address" in body:
            patient.address_json = body.get("address_json") or body.get("address")
        if "emergency_contact_json" in body or "emergencyContact" in body:
            patient.emergency_contact_json = body.get("emergency_contact_json") or body.get("emergencyContact")

        if "blood_group" in body or "bloodGroup" in body:
            patient.blood_group = str(body.get("blood_group") or body.get("bloodGroup") or "").strip() or None
        if "ward" in body:
            patient.ward = str(body.get("ward") or "").strip() or None
        if "severity" in body:
            patient.severity = str(body.get("severity") or "").strip() or None
        if "status" in body:
            patient.status = str(body.get("status") or "").strip() or None
        if "vitals" in body and isinstance(body.get("vitals"), dict):
            patient.vitals = body["vitals"]
            check_vital_thresholds(patient_id, body["vitals"])
        if "surgery_readiness" in body or "surgeryReadiness" in body:
            patient.surgery_readiness = body.get("surgery_readiness") or body.get("surgeryReadiness")

        patient.updated_at = datetime.now(timezone.utc)
        session.flush()
        out = _patient_detail(patient, include_abdm=False)
        return json_response(200, out)


def handler(event: dict, context: object) -> dict:
    """Handle GET/POST /api/v1/patients and GET/PUT /api/v1/patients/:id."""
    try:
        method = (event.get("httpMethod") or "GET").upper()
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]

        if len(parts) <= 1 and (not parts or parts[0].lower() == "patients"):
            if method == "GET":
                return _list_patients()
            if method == "POST":
                return _post_patients(event)
            return json_response(405, {"error": "Method not allowed"})

        if len(parts) >= 2 and parts[0].lower() == "v1" and parts[1].lower() == "patients":
            patient_id = parts[2] if len(parts) > 2 else None
            if patient_id:
                if method == "GET":
                    return _get_patient(patient_id)
                if method == "PUT":
                    return _put_patient(event, patient_id)
                return json_response(405, {"error": "Method not allowed"})
            if method == "POST":
                return _post_patients(event)
            return _list_patients()
        # Legacy /api/patients and /api/patients/:id (no v1 prefix)
        if len(parts) >= 2 and parts[0].lower() == "patients":
            patient_id = parts[1]
            if method == "GET":
                return _get_patient(patient_id)
            if method == "PUT":
                return _put_patient(event, patient_id)
            return json_response(405, {"error": "Method not allowed"})
        return json_response(404, {"error": "Not found"})
    except Exception as e:
        logger.error(
            "Patient handler error",
            extra={"error": str(e), "handler": "patient"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
