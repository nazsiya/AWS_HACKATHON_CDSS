"""
Engagement Agent API handler.
Reminders, escalation, sendReminder, escalateToDoctor.
"""

import json
from typing import Any

from cdss.agents.engagement_agent import EngagementAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for Engagement Agent."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "sendReminder")
    payload = body.get("payload", {})

    agent = EngagementAgent()
    actions = {
        "getReminders": agent.get_reminders,
        "getEscalations": agent.get_escalations,
        "sendReminder": agent.send_reminder,
        "escalateToDoctor": agent.escalate_to_doctor,
    }
    fn = actions.get(action, agent.send_reminder)
    result = fn(payload)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
