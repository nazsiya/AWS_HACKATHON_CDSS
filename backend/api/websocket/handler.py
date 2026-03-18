"""
CDSS WebSocket Handler — Lambda
Manages real-time clinical data streams for the doctor dashboard.

Constraint: no DynamoDB; Aurora is the only database. This handler is therefore
stateless with respect to connection storage and only sends updates back to the
current connection. When multi-client broadcasting is needed, a small Aurora
table can be added later via cdss.db.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "ap-south-1"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_management_client(event: dict):
    """Build ApiGatewayManagementApi client for this WebSocket API (post_to_connection)."""
    ctx = event.get("requestContext", {})
    domain = ctx.get("domainName")
    stage = ctx.get("stage")
    if not domain or not stage:
        return None
    endpoint = f"https://{domain}/{stage}"
    return boto3.client("apigatewaymanagementapi", endpoint_url=endpoint, region_name=AWS_REGION)


def _post_to_connection(management_client, connection_id: str, data: dict) -> bool:
    """Send data to one connection. Returns False if connection gone (stale)."""
    try:
        management_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(data).encode("utf-8"))
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "Gone":
            return False
        logger.warning("PostToConnection failed for %s: %s", connection_id, e)
        return False


def handle_connect(connection_id: str, doctor_id: Optional[str]) -> dict:
    """Acknowledge a new connection. No state persisted (Aurora-only constraint)."""
    logger.info("WebSocket connected: %s doctor=%s", connection_id, doctor_id or "UNKNOWN")
    return {"statusCode": 200, "body": "Connected"}


def handle_disconnect(connection_id: str) -> dict:
    """Acknowledge disconnect. No state persisted."""
    logger.info("WebSocket disconnected: %s", connection_id)
    return {"statusCode": 200, "body": "Disconnected"}


def handle_default(event: dict, connection_id: str) -> dict:
    """
    Handle $default route: body must be JSON with 'action'.

    Actions:
    - subscribe_surgery / subscribe_patient: acknowledged but not stored server-side.
    - checklist_update: echoed back to the same connection so the UI updates.
    """
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": "Invalid JSON"}

    action = (body.get("action") or "").strip().lower()

    if action in {"subscribe_surgery", "subscribe_patient"}:
        # Acknowledge subscription; no DB storage (Aurora-only constraint).
        payload = {
            "type": action,
            "message": "Subscription acknowledged",
            **{k: v for k, v in body.items() if k.endswith("_id")},
        }
        management = _get_management_client(event)
        if management:
            _post_to_connection(management, connection_id, payload)
        return {"statusCode": 200, "body": json.dumps(payload)}

    if action == "checklist_update":
        surgery_id = (body.get("surgery_id") or "").strip()
        checklist_item_id = body.get("checklist_item_id")
        completed = body.get("completed")
        if not surgery_id:
            return {"statusCode": 400, "body": "surgery_id required"}
        management = _get_management_client(event)
        if not management:
            return {"statusCode": 500, "body": "Management client unavailable"}
        payload = {
            "type": "checklist_update",
            "surgery_id": surgery_id,
            "checklist_item_id": checklist_item_id,
            "completed": completed,
            "message": "Checklist item updated",
        }
        _post_to_connection(management, connection_id, payload)
        return {"statusCode": 200, "body": json.dumps({"broadcast": 1, "surgery_id": surgery_id})}

    return {"statusCode": 400, "body": json.dumps({"error": "Unknown action", "action": action})}


def lambda_handler(event: dict, context: Any) -> dict:
    """Main entry point for WebSocket events ($connect, $disconnect, $default)."""
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")

    logger.info("WebSocket request: %s (%s)", route_key, connection_id)

    if route_key == "$connect":
        doctor_id = (event.get("queryStringParameters") or {}).get("doctor_id")
        return handle_connect(connection_id, doctor_id)

    if route_key == "$disconnect":
        return handle_disconnect(connection_id)

    if route_key == "$default":
        return handle_default(event, connection_id)

    # Legacy custom route for subscribe_patient if ever configured
    if route_key == "subscribe_patient":
        try:
            body = json.loads(event.get("body") or "{}")
            patient_id = (body.get("patient_id") or "").strip()
            if not patient_id:
                return {"statusCode": 400, "body": "patient_id required"}
            payload = {
                "type": "subscribe_patient",
                "message": "Subscription acknowledged",
                "patient_id": patient_id,
            }
            management = _get_management_client(event)
            if management:
                _post_to_connection(management, connection_id, payload)
            return {"statusCode": 200, "body": json.dumps(payload)}
        except json.JSONDecodeError as exc:
            logger.warning("subscribe_patient failed: %s", exc)
            return {"statusCode": 400, "body": "Invalid JSON"}

    return {"statusCode": 404, "body": "Route not found"}
