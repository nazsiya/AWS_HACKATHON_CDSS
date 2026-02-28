"""
Scheduling Agent API handler.
Appointments, OT booking, bookSlot, resolveConflict.
"""

import json
from typing import Any

from cdss.agents.scheduling_agent import SchedulingAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for Scheduling Agent."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "bookSlot")
    payload = body.get("payload", {})

    agent = SchedulingAgent()
    actions = {
        "getAppointments": agent.get_appointments,
        "bookOT": agent.book_ot,
        "bookSlot": agent.book_slot,
        "resolveConflict": agent.resolve_conflict,
    }
    fn = actions.get(action, agent.book_slot)
    result = fn(payload)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
