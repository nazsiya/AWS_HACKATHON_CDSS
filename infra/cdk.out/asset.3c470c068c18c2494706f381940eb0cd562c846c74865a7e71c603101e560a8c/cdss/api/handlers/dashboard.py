"""
Dashboard data aggregator for the Staff (doctor) web app.
Returns a dict shaped for the existing frontend dashboard widgets.
GET /dashboard returns frontend shape; uses Aurora when available, stub otherwise.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_dashboard_data() -> dict:
    """
    Aggregate dashboard data for Staff app: stats, patient queue, AI alerts.
    Tries Aurora via get_session; on failure or missing tables returns stub.
    """
    try:
        from sqlalchemy import func, select
        from cdss.db.session import get_session
        from cdss.db.models import Patient, Surgery, AuditLog
    except Exception as e:
        logger.debug("Dashboard DB imports skipped: %s", e)
        return _stub_dashboard()

    try:
        with get_session() as session:
            patient_count = session.scalar(select(func.count(Patient.id))) or 0
            surgery_count = session.scalar(select(func.count(Surgery.id))) or 0
            result = session.execute(
                select(AuditLog)
                .order_by(AuditLog.timestamp.desc())
                .limit(5)
            )
            recent_audit = result.scalars().all() if hasattr(result, "scalars") else []
            return {
                "stats": {
                    "totalPatients": patient_count,
                    "activeSurgeries": surgery_count,
                    "alertsCount": 0,
                },
                "patientQueue": [],
                "aiAlerts": [],
                "recentActivity": [
                    {"action": r.action, "resource": r.resource, "timestamp": (r.timestamp.isoformat() if r.timestamp else None)}
                    for r in recent_audit
                ],
            }
    except Exception as e:
        logger.warning("Dashboard aggregation failed, using stub: %s", e)
        return _stub_dashboard()


def _stub_dashboard() -> dict:
    """Fallback when DB is unavailable or not migrated."""
    return {
        "stats": {"totalPatients": 0, "activeSurgeries": 0, "alertsCount": 0},
        "patientQueue": [],
        "aiAlerts": [],
        "recentActivity": [],
    }
