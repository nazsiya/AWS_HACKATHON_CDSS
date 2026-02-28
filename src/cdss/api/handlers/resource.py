"""
Resource Agent API handler.
OT availability, equipment, checkOT, allocateEquipment.
"""

import json
from typing import Any

from cdss.agents.resource_agent import ResourceAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for Resource Agent."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "checkOT")
    payload = body.get("payload", {})

    agent = ResourceAgent()
    actions = {
        "getOTAvailability": agent.get_ot_availability,
        "getEquipment": agent.get_equipment,
        "checkOT": agent.check_ot,
        "allocateEquipment": agent.allocate_equipment,
    }
    fn = actions.get(action, agent.check_ot)
    result = fn(payload)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
