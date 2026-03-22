"""
Notification service wrappers.

Phase 1–2: implement SNS publish as the transport.
Higher-level channels (Pinpoint SMS/voice) can be layered later.
"""

from __future__ import annotations

import json
import os
import uuid


def _sns_publish(topic_arn: str, message: str, attributes: dict | None = None) -> dict:
    if not topic_arn:
        return {"success": False, "reason": "SNS topic not configured"}
    try:
        import boto3

        client = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        attrs = {}
        for k, v in (attributes or {}).items():
            if v is None:
                continue
            attrs[str(k)] = {"DataType": "String", "StringValue": str(v)}
        resp = client.publish(TopicArn=topic_arn, Message=message, MessageAttributes=attrs or None)
        return {"success": True, "message_id": resp.get("MessageId")}
    except Exception as exc:
        return {"success": False, "reason": str(exc)}


def send_doctor_escalation(doctor_id: str, alert_type: str, context: dict | None = None) -> dict:
    """
    Publish an escalation/alert for doctors/admins.
    """
    topic = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()
    trace_id = str(uuid.uuid4())
    payload = {
        "type": "doctor_escalation",
        "doctor_id": doctor_id,
        "alert_type": alert_type,
        "context": context or {},
        "trace_id": trace_id,
    }
    result = _sns_publish(topic, json.dumps(payload), {"alert_type": alert_type, "trace_id": trace_id})
    result["trace_id"] = trace_id
    return result


def send_surgery_alert(surgery_id: str, alert_type: str, context: dict | None = None) -> dict:
    """
    Publish surgery workflow alerts.
    For Phase 1–2 we reuse the doctor escalations topic.
    """
    return send_doctor_escalation(
        doctor_id="surgery",
        alert_type=alert_type,
        context={"surgery_id": surgery_id, **(context or {})},
    )


def send_patient_reminder(patient_id: str, message: str, reminder_type: str, language: str = "en", metadata: dict | None = None) -> dict:
    """
    Publish patient reminders. If patient reminders topic is not configured, fall back to doctor escalations topic.
    """
    topic = os.environ.get("SNS_TOPIC_PATIENT_REMINDERS_ARN", "").strip()
    if not topic:
        topic = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()
    trace_id = str(uuid.uuid4())
    payload = {
        "type": "patient_reminder",
        "patient_id": patient_id,
        "reminder_type": reminder_type,
        "language": language,
        "message": message,
        "metadata": metadata or {},
        "trace_id": trace_id,
    }
    result = _sns_publish(topic, json.dumps(payload), {"reminder_type": reminder_type, "trace_id": trace_id})
    result["trace_id"] = trace_id
    return result

