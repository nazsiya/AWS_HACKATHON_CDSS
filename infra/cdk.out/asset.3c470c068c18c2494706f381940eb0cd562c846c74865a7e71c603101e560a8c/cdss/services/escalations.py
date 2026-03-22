"""
Escalation service for critical alerts (Requirement 5.3).
Tracks multi-channel notifications and logs acknowledgment response times.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from cdss.db.session import get_session
from cdss.db.models import EscalationLog

logger = logging.getLogger(__name__)


def trigger_escalation_sequence(alert_id: str, severity: str) -> None:
    """
    Initiate an escalation sequence for a critical alert.
    In production, this would be managed by a state machine or task queue.
    """
    try:
        with get_session() as session:
            # Level 1: In-app notification
            esc = EscalationLog(
                alert_id=alert_id,
                level=1,
                channel="APP",
                sent_at=datetime.now(timezone.utc),
            )
            session.add(esc)
            session.flush()
            logger.info("Escalation L1 (APP) triggered for alert=%s", alert_id)

            # Planned escalations if not acknowledged:
            # L2: SMS (after 5 mins)
            # L3: Voice Call (after 15 mins)
    except Exception as e:
        logger.warning("Failed to log escalation: %s", e)


def acknowledge_alert(alert_id: str, user_id: str) -> Dict[str, Any]:
    """
    Acknowledge an alert and record the response time (Req 5.3).
    """
    now = datetime.now(timezone.utc)
    try:
        with get_session() as session:
            from sqlalchemy import select

            stmt = (
                select(EscalationLog)
                .where(EscalationLog.alert_id == alert_id)
                .order_by(EscalationLog.level.desc())
            )
            esc = session.execute(stmt).scalars().first()

            if not esc:
                return {"success": False, "error": "No escalation record found"}

            if esc.acknowledged_at:
                return {"success": True, "already_acknowledged": True}

            esc.acknowledged_at = now
            delta = now - esc.sent_at
            esc.response_time_sec = int(delta.total_seconds())
            session.flush()

            logger.info(
                "Alert %s acknowledged by %s in %ds",
                alert_id,
                user_id,
                esc.response_time_sec,
            )
            return {
                "success": True,
                "response_time_sec": esc.response_time_sec,
                "level": esc.level,
            }
    except Exception as e:
        logger.error("Acknowledgment failed: %s", e)
        return {"success": False, "error": str(e)}
