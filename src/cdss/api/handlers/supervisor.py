"""
Supervisor API handler.
Routes intents to sub-agents and aggregates responses.
"""

import json
from typing import Any

from cdss.agents.supervisor import SupervisorAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for supervisor (routeIntent / aggregateResponse)."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "route")
    payload = body.get("payload", {})

    agent = SupervisorAgent()
    if action == "route":
        result = agent.route_intent(payload.get("intent", ""), payload)
    else:
        result = agent.aggregate_response(payload.get("responses", []))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
