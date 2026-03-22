"""
Doctor activity log endpoint.

POST /api/v1/activity

Best-effort write of doctor-linked activity into the existing AuditLog table.
Used by the doctor web app's ActivityContext for "My Activity".
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from cdss.api.handlers.common import json_response, parse_body_json
from cdss.db.models import AuditLog
from cdss.db.session import get_session

logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /api/v1/activity.

    Body:
      - doctor_id: str (required)
      - action: str (required) – activity type, e.g. "view_patient", "open_dashboard"
      - patient_id: str (optional)
      - resource: str (optional) – REST resource or UI location
      - detail: str (optional) – short, non-PHI description

    Writes a row into AuditLog.details; never fails the request because of audit issues.
    """
    method = (event.get("httpMethod") or "POST").upper()
    if method != "POST":
        return json_response(405, {"error": "Method not allowed"})

    body = parse_body_json(event)
    doctor_id = (body.get("doctor_id") or "").strip()
    action = (body.get("action") or "").strip()
    if not doctor_id or not action:
        return json_response(400, {"error": "doctor_id and action are required"})

    patient_id = (body.get("patient_id") or "").strip() or None
    resource = (body.get("resource") or "").strip() or "/api/v1/activity"
    detail = (body.get("detail") or "").strip() or None

    timestamp = datetime.now(timezone.utc)
    details: Dict[str, Any] = {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "detail": detail,
        "source": "doctor-activity-endpoint",
    }

    try:
        with get_session() as session:
            record = AuditLog(
                user_id=doctor_id,
                user_email=None,
                action=action,
                resource=resource,
                timestamp=timestamp,
                details=details,
            )
            session.add(record)
    except Exception as exc:
        logger.warning(
            "Doctor activity audit write failed",
            extra={"error": str(exc), "doctor_id": doctor_id, "resource": resource},
        )

    return json_response(
        201,
        {
            "ok": True,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "action": action,
            "resource": resource,
        },
        event=event,
    )

