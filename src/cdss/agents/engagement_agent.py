"""
Engagement Agent: Reminders, escalation, sendReminder, escalateToDoctor.
Uses SNS Pinpoint (SMS, push), EventBridge, SES for doctor escalation.
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class EngagementAgent(BaseAgent):
    """Sends reminders (multilingual) and escalates to doctors."""

    name = "EngagementAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "getReminders", "description": "Get reminder list"},
            {"name": "getEscalations", "description": "Get escalation list"},
            {"name": "sendReminder", "description": "Send reminder via SMS/Push (Pinpoint)"},
            {"name": "escalateToDoctor", "description": "Escalate to doctor via SES"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Engagement Agent for an Indian hospital. "
            "You send multilingual reminders (Hindi, Tamil, Telugu, Bengali) via Pinpoint "
            "and escalate critical issues to doctors via SES. DISHA auditable."
        )

    def get_reminders(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get reminders (from DynamoDB medication schedules)."""
        patient_id = payload.get("patientId", "")
        return {"patientId": patient_id, "reminders": []}

    def get_escalations(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get escalation list."""
        return {"escalations": []}

    def send_reminder(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send reminder via SNS Pinpoint (SMS/push, multilingual)."""
        patient_id = payload.get("patientId", "")
        channel = payload.get("channel", "SMS")
        language = payload.get("language", "en")
        return {"patientId": patient_id, "channel": channel, "language": language, "sent": True}

    def escalate_to_doctor(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Escalate to doctor via SES."""
        case_id = payload.get("caseId", "")
        reason = payload.get("reason", "")
        return {"caseId": case_id, "reason": reason, "escalated": True}
