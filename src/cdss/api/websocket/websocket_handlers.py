"""
WebSocket connection handler for real-time surgical planning.
Can be used with API Gateway WebSocket API or ECS Fargate container.
"""

import json
from typing import Any


def connect_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $connect route."""
    connection_id = event.get("requestContext", {}).get("connectionId", "")
    return {"statusCode": 200, "body": json.dumps({"connectionId": connection_id})}


def disconnect_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $disconnect route."""
    return {"statusCode": 200, "body": ""}


def default_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle default WebSocket message (surgery plan updates, OT checklist sync)."""
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)
    action = body.get("action", "")
    # Route to surgery planning / resource agents as needed
    return {"statusCode": 200, "body": json.dumps({"received": action})}
