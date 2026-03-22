"""
Alert engine – central service for clinical alerts and notifications (Req 9).

Provides:
  - emit_alert(severity, alert_type, channel, payload) → routes to SNS topics
  - Persists alerts to RDS alert_log table for audit
  - Severity-based routing: critical → emergency, high → doctor, medium/low → standard

Per CDSS.mdc: trace review and medical audit for all alert-producing events.
Per project-conventions.mdc: no PHI in logs; audit trails for clinical actions.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def check_vital_thresholds(patient_id: str, vitals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check vitals against safety thresholds and emit critical alert if exceeded (Req 5.2).
    Returns the alert result if an alert was emitted, else None.
    """
    # Basic clinical thresholds for emergency triggers
    hr = vitals.get("heart_rate") or vitals.get("heartRate")
    bp_sys = vitals.get("blood_pressure_sys") or vitals.get("bloodPressureSys")
    spo2 = vitals.get("oxygen_saturation") or vitals.get("spo2")

    triggers = []
    if hr and isinstance(hr, (int, float)):
        if hr > 130: triggers.append(f"Tachycardia ({hr})")
        if hr < 45: triggers.append(f"Bradycardia ({hr})")
    if bp_sys and isinstance(bp_sys, (int, float)):
        if bp_sys > 190: triggers.append(f"Hypertensive Crisis ({bp_sys} sys)")
        if bp_sys < 85: triggers.append(f"Severe Hypotension ({bp_sys} sys)")
    if spo2 and isinstance(spo2, (int, float)):
        if spo2 < 90: triggers.append(f"Critical Hypoxia ({spo2}%)")

    if triggers:
        message = "Emergency Protocol Triggered: " + "; ".join(triggers)
        return emit_alert(
            severity="critical",
            alert_type="critical_vitals",
            channel="emergency",
            patient_id=patient_id,
            message=message,
            context={"vitals": vitals, "triggers": triggers},
        )
    return None


def emit_alert(
    severity: str,
    alert_type: str,
    channel: str = "doctor",
    patient_id: str = "",
    doctor_id: str = "",
    message: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Central alert dispatcher. Routes by severity to SNS topics and persists to RDS.

    Args:
        severity: critical, high, medium, low
        alert_type: e.g. drug_interaction, critical_vitals, non_adherence, surgical_complication
        channel: doctor, pharmacist, emergency
        patient_id: Patient identifier (for audit linking)
        doctor_id: Doctor identifier (for audit linking)
        message: Human-readable alert message
        context: Additional structured data

    Returns:
        dict with alert_id, success, and optionally sns_result
    """
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    ctx = context or {}

    # Build alert payload
    payload = {
        "alert_id": alert_id,
        "severity": severity,
        "alert_type": alert_type,
        "channel": channel,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "message": message,
        "context": ctx,
        "timestamp": now.isoformat(),
    }

    # 1. Persist to RDS alert_log
    _persist_alert(payload)

    # 2. Route to SNS by severity
    sns_result = _route_to_sns(severity, channel, payload)

    # 3. Trigger escalation if critical (Req 5.3)
    if severity == "critical":
        try:
            from cdss.services.escalations import trigger_escalation_sequence
            trigger_escalation_sequence(alert_id, severity)
        except Exception as e:
            logger.warning("Escalation trigger failed: %s", e)

    # 3. Audit log (no PHI in message)
    logger.info(
        "Alert emitted alert_id=%s severity=%s type=%s channel=%s",
        alert_id, severity, alert_type, channel,
        extra={"alert_id": alert_id, "severity": severity, "alert_type": alert_type},
    )

    return {
        "alert_id": alert_id,
        "success": True,
        "severity": severity,
        "alert_type": alert_type,
        "sns_result": sns_result,
    }


def _persist_alert(payload: Dict[str, Any]) -> None:
    """Persist alert to RDS alert_log table. Fails silently if DB unavailable."""
    try:
        from cdss.db.session import get_session
        from cdss.db.models import AlertLog

        with get_session() as session:
            log_entry = AlertLog(
                alert_id=payload["alert_id"],
                severity=payload["severity"],
                alert_type=payload["alert_type"],
                channel=payload["channel"],
                patient_id=payload.get("patient_id") or None,
                doctor_id=payload.get("doctor_id") or None,
                message=payload.get("message", ""),
                payload=payload.get("context", {}),
                created_at=datetime.now(timezone.utc),
            )
            session.add(log_entry)
            session.flush()
    except Exception as e:
        logger.warning("Alert persistence failed (non-fatal): %s", e)


def _route_to_sns(severity: str, channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route alert to appropriate SNS topic based on severity and channel."""
    from cdss.services.notifications import _sns_publish

    # Choose topic based on severity
    if severity == "critical":
        topic_arn = os.environ.get("SNS_TOPIC_EMERGENCY_ARN", "").strip()
        if not topic_arn:
            topic_arn = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()
    elif channel == "pharmacist":
        topic_arn = os.environ.get("SNS_TOPIC_PHARMACIST_ARN", "").strip()
        if not topic_arn:
            topic_arn = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()
    else:
        topic_arn = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()

    if not topic_arn:
        return {"success": False, "reason": "No SNS topic configured for this alert type"}

    return _sns_publish(
        topic_arn,
        json.dumps(payload),
        {
            "alert_type": payload["alert_type"],
            "severity": payload["severity"],
            "alert_id": payload["alert_id"],
        },
    )
