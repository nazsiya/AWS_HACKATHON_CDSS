"""
Tasks handler – aggregate pending clinical tasks for the doctor dashboard.

GET /api/v1/tasks → list pending tasks from surgeries, reminders, medications, visits.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from cdss.api.handlers.common import json_response
from cdss.db.session import get_session

logger = logging.getLogger(__name__)


def _list_tasks(event: dict) -> dict:
    """
    GET /api/v1/tasks — aggregate pending tasks.

    Returns tasks from:
    - Upcoming surgeries (status=scheduled) → "Pre-op check" or "Surgery prep"
    - Unsent reminders → "Medication reminder"
    - Recent visits without notes → "Follow-up needed"
    """
    tasks = []

    try:
        from sqlalchemy import select, func
        from cdss.db.models import Surgery, Patient, Reminder, Medication, Visit

        with get_session() as session:
            # 1. Upcoming surgeries → tasks
            surgery_stmt = (
                select(Surgery, Patient.name)
                .outerjoin(Patient, Surgery.patient_id == Patient.id)
                .where(Surgery.status.in_(["scheduled", "pre-op"]))
                .order_by(Surgery.scheduled_date.asc().nullslast())
                .limit(20)
            )
            surgery_rows = session.execute(surgery_stmt).all()
            for surg, pname in surgery_rows:
                priority = "High" if surg.status == "pre-op" else "Medium"
                tasks.append({
                    "id": f"task-surg-{surg.id}",
                    "priority": priority,
                    "taskType": "Pre-op check" if surg.status == "scheduled" else "Surgery preparation",
                    "patientName": pname or "Unknown",
                    "source": "surgery",
                    "sourceId": surg.id,
                })

            # 2. Unsent reminders → tasks
            reminder_stmt = (
                select(Reminder, Patient.name)
                .outerjoin(Patient, Reminder.patient_id == Patient.id)
                .where(Reminder.sent_at.is_(None))
                .order_by(Reminder.reminder_at.asc().nullslast())
                .limit(10)
            )
            reminder_rows = session.execute(reminder_stmt).all()
            for rem, pname in reminder_rows:
                tasks.append({
                    "id": f"task-rem-{rem.id}",
                    "priority": "Medium",
                    "taskType": "Medication reminder",
                    "patientName": pname or "Unknown",
                    "source": "reminder",
                    "sourceId": rem.id,
                })

            # 3. Recent visits needing follow-up (visits in last 7 days with no notes)
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date()
            visit_stmt = (
                select(Visit, Patient.name)
                .outerjoin(Patient, Visit.patient_id == Patient.id)
                .where(Visit.visit_date >= seven_days_ago)
                .where(
                    (Visit.notes.is_(None)) | (Visit.notes == "")
                )
                .order_by(Visit.visit_date.desc())
                .limit(10)
            )
            visit_rows = session.execute(visit_stmt).all()
            for visit, pname in visit_rows:
                tasks.append({
                    "id": f"task-visit-{visit.id}",
                    "priority": "Low",
                    "taskType": "Follow-up documentation",
                    "patientName": pname or "Unknown",
                    "source": "visit",
                    "sourceId": visit.id,
                })

    except Exception as e:
        logger.warning("Tasks aggregation failed: %s", e, exc_info=True)
        # Return empty list; dashboard falls back gracefully
        return json_response(200, {"tasks": [], "_error": str(e)}, event=event)

    # Sort by priority (High > Medium > Low)
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    tasks.sort(key=lambda t: priority_order.get(t.get("priority", "Low"), 3))

    return json_response(200, {"tasks": tasks}, event=event)


def handler(event: dict, context: object) -> dict:
    """Handle GET /api/v1/tasks."""
    method = (event.get("httpMethod") or "GET").upper()
    if method == "GET":
        return _list_tasks(event)
    return json_response(405, {"error": "Method not allowed"}, event=event)
