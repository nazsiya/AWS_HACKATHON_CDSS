"""
Engagement agent handler – medications, reminders, consultations from Aurora.

GET /api/v1/medications: from Aurora (Medication + Patient name).
GET /api/v1/consultations/:visitId: single visit with summary and extracted_entities (Phase 7).
POST /api/v1/consultations/:visitId/generate-summary: generate summary + entities via Bedrock, store on Visit (Phase 7).
POST /api/v1/reminders/nudge: record nudge; optional SNS/EventBridge.
POST /api/v1/reminders: create Reminder in DB.
GET /api/v1/reminders/adherence: adherence stats for patient_id query param (Phase 7).
POST /api/v1/consultations/start: create Visit (patient_id, doctor_id).
POST /api/v1/consultations: create or update Visit (notes, summary).
Per project-conventions: audit and no PHI in logs.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import select

from cdss.api.handlers.common import json_response, parse_body_json
from cdss.db.models import Medication, Patient, Reminder, Visit
from cdss.db.session import get_session
from cdss.services.i18n import get_request_language, translate_for_patient
from cdss.services.notifications import send_patient_reminder

logger = logging.getLogger(__name__)


def _upload_transcript_if_present(patient_id: str, visit_id: int, body: dict) -> str | None:
    """If body contains transcript/text, upload to S3 and return key; else None. No PHI in logs."""
    transcript = body.get("transcript") or body.get("transcriptText")
    if transcript is None or (isinstance(transcript, str) and not transcript.strip()):
        return None
    text = transcript if isinstance(transcript, str) else str(transcript)
    try:
        from cdss.s3.documents import put_consultation_transcript
        return put_consultation_transcript(patient_id, visit_id, text)
    except (ValueError, Exception) as e:
        logger.warning("S3 transcript upload skipped or failed", extra={"error": str(e)})
        return None


def _serialize_datetime(d: datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def _medication_item(med: Medication, patient_name: str | None) -> dict:
    """One medication for frontend (id, patient, medication, frequency, nextDose, status, interactions)."""
    return {
        "id": f"MED-{med.id}",
        "patient": patient_name or "—",
        "medication": med.medication_name,
        "frequency": med.frequency or "—",
        "nextDose": _serialize_datetime(med.next_dose_at),
        "status": med.status,
        "interactions": [],
    }


def _list_medications() -> dict:
    """Return medications from Aurora with patient name."""
    with get_session() as session:
        stmt = (
            select(Medication, Patient.name)
            .join(Patient, Medication.patient_id == Patient.id)
            .order_by(Medication.patient_id, Medication.id)
        )
        rows = session.execute(stmt).all()
        list_data = [_medication_item(med, pname) for med, pname in rows]
        return json_response(200, {"medications": list_data})


def _post_medications(event: dict) -> dict:
    """POST /api/v1/medications – prescribe a new medication (Req 5.1 & 6)."""
    body = parse_body_json(event)
    patient_id = body.get("patient_id") or body.get("patientId")
    med_name = body.get("medication_name") or body.get("medicationName")
    frequency = body.get("frequency")

    if not patient_id or not med_name:
        return json_response(400, {"error": "patient_id and medication_name required"})

    # Check for drug interactions (Req 5.1)
    from cdss.services.drug_interactions import check_drug_interactions

    interactions_result = check_drug_interactions(patient_id, med_name)

    with get_session() as session:
        med = Medication(
            patient_id=patient_id,
            medication_name=med_name,
            frequency=frequency,
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        session.add(med)
        session.flush()

        return json_response(
            201,
            {
                "ok": True,
                "medicationId": med.id,
                "interactions": interactions_result.get("interactions", []),
                "alert_ids": interactions_result.get("alert_ids", []),
            },
        )


def _post_reminders_nudge(event: dict) -> dict:
    """POST .../reminders/nudge – send nudge via SNS and record."""
    body = parse_body_json(event)
    patient_id = body.get("patient_id") or body.get("patientId")
    medication_id = body.get("medication_id") or body.get("medicationId")
    if not patient_id:
        return json_response(400, {"error": "patient_id required"})

    # Get patient language for localized nudge
    patient_lang = "en"
    try:
        with get_session() as session:
            patient = session.get(Patient, patient_id)
            if patient:
                patient_lang = str(getattr(patient, "language", None) or "en").strip().lower() or "en"
    except Exception:
        pass

    nudge_message = "Time for your medication. Please take your prescribed dose."
    translated = translate_for_patient(nudge_message, patient_lang)

    # Send via SNS
    result = send_patient_reminder(
        patient_id=patient_id,
        message=translated,
        reminder_type="nudge",
        language=patient_lang,
        metadata={"medication_id": medication_id} if medication_id else None,
    )

    return json_response(200, {
        "ok": True,
        "message": "Nudge sent",
        "notification": result,
    })


def _post_reminders(event: dict) -> dict:
    """POST .../reminders – create Reminder in DB."""
    body = parse_body_json(event)
    patient_id = body.get("patient_id") or body.get("patientId")
    medication_id = body.get("medication_id") or body.get("medicationId")
    scheduled_at = body.get("scheduled_at") or body.get("scheduledAt")
    if not patient_id or not scheduled_at:
        return json_response(400, {"error": "patient_id and scheduled_at required"})
    try:
        from datetime import datetime
        rem_at = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return json_response(400, {"error": "Invalid scheduled_at"})
    with get_session() as session:
        reminder = Reminder(
            patient_id=patient_id,
            medication_id=int(medication_id) if medication_id else None,
            reminder_at=rem_at,
            created_at=datetime.now(timezone.utc),
        )
        session.add(reminder)
        session.flush()

    # Also send notification via SNS
    patient_lang = "en"
    try:
        with get_session() as session:
            patient = session.get(Patient, patient_id)
            if patient:
                patient_lang = str(getattr(patient, "language", None) or "en").strip().lower() or "en"
    except Exception:
        pass

    reminder_msg = f"Reminder: You have a medication scheduled at {scheduled_at}."
    translated_msg = translate_for_patient(reminder_msg, patient_lang)
    notif_result = send_patient_reminder(
        patient_id=patient_id,
        message=translated_msg,
        reminder_type="medication",
        language=patient_lang,
        metadata={"medication_id": medication_id, "scheduled_at": scheduled_at},
    )

    return json_response(200, {"ok": True, "message": "Reminder scheduled", "notification": notif_result})


def _post_consultations_start(event: dict) -> dict:
    """POST .../consultations/start – create Visit for patient_id, doctor_id; return AI summary when available.
    doctor_id is optional: if missing, use Cognito sub from request context or placeholder so Start consultation always works.
    Returns 503 with a clear message if DB is unavailable (so UI shows that instead of generic HTTP 500)."""
    body = parse_body_json(event)
    patient_id = body.get("patient_id") or body.get("patientId")
    doctor_id = body.get("doctor_id") or body.get("doctorId")
    if not patient_id:
        return json_response(400, {"error": "patient_id required"})
    if not doctor_id:
        request_ctx = (event.get("requestContext") or {}).get("authorizer") or {}
        claims = request_ctx.get("claims") or request_ctx
        doctor_id = claims.get("sub") or "DOC-CURRENT"
    try:
        with get_session() as session:
            visit = Visit(
                patient_id=patient_id,
                doctor_id=doctor_id,
                visit_date=date.today(),
                created_at=datetime.now(timezone.utc),
            )
            session.add(visit)
            session.flush()
            visit_id = visit.id
            s3_key = _upload_transcript_if_present(patient_id, visit_id, body)
            if s3_key:
                visit.transcript_s3_key = s3_key

            # AI summary: optional; never fail the request if Bedrock/DB read fails
            ai_summary = None
            try:
                patient = session.get(Patient, patient_id)
                if patient:
                    from sqlalchemy import select
                    from cdss.bedrock.patient_summary import get_patient_summary
                    recent = list(
                        session.scalars(
                            select(Visit)
                            .where(Visit.patient_id == patient_id)
                            .order_by(Visit.visit_date.desc())
                            .limit(5)
                        ).all()
                    )
                    ai_summary = get_patient_summary(patient, recent)
            except Exception as e:
                logger.debug("Consultation start AI summary skipped: %s", e)

        return json_response(200, {
            "visitId": visit_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "summary": ai_summary or "",
            "ai_summary": ai_summary or "",
        })
    except Exception as e:
        logger.warning("Consultation start failed (DB or session): %s", e)
        return json_response(503, {
            "error": "Database temporarily unavailable. Check RDS connectivity and tunnel.",
            "message": "Database temporarily unavailable. Check RDS connectivity and tunnel.",
        })


def _post_consultations(event: dict) -> dict:
    """POST .../consultations – create or update Visit (notes, summary); optional transcript to S3."""
    body = parse_body_json(event)
    patient_id = body.get("patient_id") or body.get("patientId")
    visit_id = body.get("visit_id") or body.get("visitId")
    notes = body.get("notes")
    summary = body.get("summary")
    if not patient_id:
        return json_response(400, {"error": "patient_id required"})
    with get_session() as session:
        if visit_id:
            stmt = select(Visit).where(Visit.id == int(visit_id), Visit.patient_id == patient_id)
            visit = session.scalar(stmt)
            if visit is None:
                return json_response(404, {"error": "Visit not found"})
            if notes is not None:
                visit.notes = notes
            if summary is not None:
                visit.summary = summary
            s3_key = _upload_transcript_if_present(patient_id, visit.id, body)
            if s3_key:
                visit.transcript_s3_key = s3_key
        else:
            doctor_id = body.get("doctor_id") or body.get("doctorId") or ""
            visit = Visit(
                patient_id=patient_id,
                doctor_id=doctor_id,
                visit_date=date.today(),
                notes=notes,
                summary=summary,
                created_at=datetime.now(timezone.utc),
            )
            session.add(visit)
            session.flush()
            s3_key = _upload_transcript_if_present(patient_id, visit.id, body)
            if s3_key:
                visit.transcript_s3_key = s3_key
        return json_response(200, {"ok": True, "visitId": visit.id})


def _visit_to_item(visit: Visit, patient_name: str | None) -> dict:
    """Single visit for GET /consultations/:id (summary, extracted_entities)."""
    return {
        "id": visit.id,
        "patient_id": visit.patient_id,
        "patient": patient_name or "—",
        "doctor_id": visit.doctor_id,
        "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
        "notes": visit.notes,
        "summary": visit.summary,
        "extracted_entities": visit.extracted_entities,
        "created_at": _serialize_datetime(visit.created_at),
    }


def _get_consultation(visit_id: str) -> dict:
    """GET /consultations/:visitId – return single visit with summary and extracted_entities."""
    try:
        vid = int(visit_id)
    except (TypeError, ValueError):
        return json_response(400, {"error": "Invalid visit ID"})
    with get_session() as session:
        stmt = (
            select(Visit, Patient.name)
            .join(Patient, Visit.patient_id == Patient.id)
            .where(Visit.id == vid)
        )
        row = session.execute(stmt).first()
        if row is None:
            return json_response(404, {"error": "Visit not found"})
        visit, pname = row
        return json_response(200, _visit_to_item(visit, pname))


def _post_consultation_generate_summary(event: dict, visit_id: str) -> dict:
    """POST /consultations/:visitId/generate-summary – Bedrock summary + entity extraction, store on Visit."""
    try:
        vid = int(visit_id)
    except (TypeError, ValueError):
        return json_response(400, {"error": "Invalid visit ID"})
    with get_session() as session:
        stmt = select(Visit).where(Visit.id == vid)
        visit = session.scalar(stmt)
        if visit is None:
            return json_response(404, {"error": "Visit not found"})
        transcript_text = None
        if visit.transcript_s3_key:
            try:
                from cdss.s3.documents import get_consultation_transcript
                transcript_text = get_consultation_transcript(visit.transcript_s3_key)
            except Exception as e:
                logger.warning("S3 transcript fetch failed: %s", e)
        if not transcript_text and visit.notes:
            transcript_text = visit.notes
        if not (transcript_text or "").strip():
            return json_response(400, {"error": "No transcript or notes to summarize"})
        from cdss.bedrock.visit_summary import generate_visit_summary, extract_medical_entities
        patient_context = ""
        try:
            stmt_p = select(Patient).where(Patient.id == visit.patient_id)
            p = session.scalar(stmt_p)
            if p and getattr(p, "conditions", None):
                patient_context = ", ".join(p.conditions) if isinstance(p.conditions, list) else str(p.conditions)
        except Exception:
            pass
        summary = generate_visit_summary(transcript_text, patient_context)
        entities = extract_medical_entities(transcript_text)
        if summary is not None:
            visit.summary = summary
        if entities is not None:
            visit.extracted_entities = entities
        session.flush()
        return json_response(200, {
            "visitId": visit.id,
            "summary": summary,
            "extracted_entities": entities,
            "message": "Summary and entities generated.",
        })


def _get_adherence(event: dict) -> dict:
    """GET /reminders/adherence?patient_id= – reminder/adherence stats for patient (Phase 7)."""
    params = event.get("queryStringParameters") or {}
    patient_id = (params.get("patient_id") or params.get("patientId") or "").strip()
    if not patient_id:
        return json_response(400, {"error": "patient_id required"})
    now = datetime.now(timezone.utc)
    with get_session() as session:
        from sqlalchemy import func

        total = session.scalar(
            select(func.count(Reminder.id)).where(Reminder.patient_id == patient_id)
        ) or 0
        sent = session.scalar(
            select(func.count(Reminder.id)).where(
                Reminder.patient_id == patient_id,
                Reminder.sent_at.isnot(None),
            )
        ) or 0
        overdue = session.scalar(
            select(func.count(Reminder.id)).where(
                Reminder.patient_id == patient_id,
                Reminder.sent_at.is_(None),
                Reminder.reminder_at < now,
            )
        ) or 0
        return json_response(200, {
            "patient_id": patient_id,
            "reminders_total": total,
            "reminders_sent": sent,
            "reminders_overdue": overdue,
            "adherence_pct": round(100.0 * sent / total, 1) if total else 0,
        })


def handler(event: dict, context: object) -> dict:
    """Handle medications, reminders, and consultations."""
    try:
        method = (event.get("httpMethod") or "GET").upper()
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]

        if len(parts) < 2 or parts[0].lower() != "v1":
            return json_response(404, {"error": "Not found"})

        seg = parts[1].lower()

        if seg == "medications":
            if method == "GET":
                return _list_medications()
            if method == "POST":
                return _post_medications(event)
            return json_response(405, {"error": "Method not allowed"})

        if seg == "reminders":
            if method == "GET":
                if len(parts) > 2 and parts[2].lower() == "adherence":
                    return _get_adherence(event)
                return json_response(405, {"error": "Method not allowed"})
            if method == "POST":
                if len(parts) > 2 and parts[2].lower() == "nudge":
                    return _post_reminders_nudge(event)
                return _post_reminders(event)
            return json_response(405, {"error": "Method not allowed"})

        if seg == "consultations":
            if len(parts) >= 3 and parts[2].isdigit():
                visit_id = parts[2]
                if method == "GET":
                    return _get_consultation(visit_id)
                if method == "POST" and len(parts) > 3 and parts[3].lower() == "generate-summary":
                    return _post_consultation_generate_summary(event, visit_id)
            if method != "POST":
                return json_response(405, {"error": "Method not allowed"})
            if len(parts) > 2 and parts[2].lower() == "start":
                return _post_consultations_start(event)
            return _post_consultations(event)

        return json_response(404, {"error": "Not found"})
    except Exception as e:
        logger.error(
            "Engagement handler error",
            extra={"error": str(e), "handler": "engagement"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
