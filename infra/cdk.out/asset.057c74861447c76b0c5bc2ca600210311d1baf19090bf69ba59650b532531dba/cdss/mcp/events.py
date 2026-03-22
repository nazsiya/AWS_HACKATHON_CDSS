"""
EventBridge publish client for MCP-style inter-agent communication.

Publishes validated Pydantic messages to the CDSS event bus with Source "cdss.agents".
Every event Detail includes trace_id for audit. Use schemas from cdss.mcp.schemas
for request types and validation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from cdss.mcp.schemas import (
    DETAIL_TYPE_TO_MODEL,
    BaseMCPMessage,
)

logger = logging.getLogger(__name__)

# EventBridge Source for CDSS agents; must match rule in infrastructure/notifications.tf
EVENT_SOURCE = "cdss.agents"

# Map request model class -> DetailType for put_events
_MODEL_TO_DETAIL_TYPE: dict[type[BaseMCPMessage], str] = {
    model_cls: detail_type for detail_type, model_cls in DETAIL_TYPE_TO_MODEL.items()
}


def _get_detail_type(message: BaseMCPMessage) -> str:
    """Resolve EventBridge DetailType from the message model. Raises ValueError if unknown."""
    detail_type = _MODEL_TO_DETAIL_TYPE.get(type(message))
    if detail_type is None:
        raise ValueError(
            f"Unknown MCP message type for EventBridge: {type(message).__name__}. "
            "Message must be one of the typed request models from cdss.mcp.schemas."
        )
    return detail_type


def publish(
    message: BaseMCPMessage,
    event_bus_name: str,
    *,
    client: Optional[Any] = None,
    region_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Publish a single MCP message to EventBridge.

    Validates that the message is a known typed request, serializes it to JSON
    (including trace_id in the Detail for audit), and calls PutEvents with
    Source "cdss.agents" and the schema-derived DetailType.

    Args:
        message: Validated Pydantic message (e.g. PatientProfileRequest).
        event_bus_name: Event bus name (e.g. from env EVENT_BUS_NAME).
        client: Optional boto3 events client; created if not provided.
        region_name: Optional region for the client when created internally.

    Returns:
        PutEvents API response (Entries, FailedEntryCount, etc.).

    Raises:
        ValueError: If message type is not a known MCP request type.
        ClientError: On EventBridge API failure.
    """
    detail_type = _get_detail_type(message)
    # Detail is JSON string; full message includes trace_id, source_agent, target_agent, etc.
    detail_json = message.model_dump_json()

    events_client = client or boto3.client(
        "events", region_name=region_name or boto3.DEFAULT_SESSION.region_name
    )

    entry = {
        "EventBusName": event_bus_name,
        "Source": EVENT_SOURCE,
        "DetailType": detail_type,
        "Detail": detail_json,
    }

    try:
        response = events_client.put_events(Entries=[entry])
    except ClientError as e:
        logger.error(
            "EventBridge PutEvents failed",
            extra={"detail_type": detail_type, "trace_id": message.trace_id},
            exc_info=True,
        )
        raise

    failed = response.get("FailedEntryCount", 0)
    if failed > 0:
        for err_entry in response.get("Entries", []):
            if "ErrorCode" in err_entry or "ErrorMessage" in err_entry:
                logger.error(
                    "EventBridge entry failed",
                    extra={
                        "trace_id": message.trace_id,
                        "detail_type": detail_type,
                        "error_code": err_entry.get("ErrorCode"),
                        "error_message": err_entry.get("ErrorMessage"),
                    },
                )
    else:
        logger.info(
            "Published MCP event",
            extra={
                "trace_id": message.trace_id,
                "detail_type": detail_type,
                "source_agent": message.source_agent,
                "target_agent": message.target_agent,
            },
        )

    return response


def publish_batch(
    messages: list[BaseMCPMessage],
    event_bus_name: str,
    *,
    client: Optional[Any] = None,
    region_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Publish up to 10 MCP messages in a single PutEvents call.

    Each message is serialized with trace_id in the Detail. Entries beyond 10
    are not sent; use multiple calls if needed.

    Args:
        messages: List of validated MCP request messages (max 10).
        event_bus_name: Event bus name.
        client: Optional boto3 events client.
        region_name: Optional region when creating client.

    Returns:
        PutEvents API response.
    """
    events_client = client or boto3.client(
        "events", region_name=region_name or boto3.DEFAULT_SESSION.region_name
    )

    entries = []
    for msg in messages[:10]:
        detail_type = _get_detail_type(msg)
        entries.append(
            {
                "EventBusName": event_bus_name,
                "Source": EVENT_SOURCE,
                "DetailType": detail_type,
                "Detail": msg.model_dump_json(),
            }
        )

    if not entries:
        return {"FailedEntryCount": 0, "Entries": []}

    try:
        response = events_client.put_events(Entries=entries)
    except ClientError as e:
        logger.error(
            "EventBridge PutEvents batch failed",
            extra={"entry_count": len(entries), "trace_ids": [m.trace_id for m in messages[:10]]},
            exc_info=True,
        )
        raise

    failed = response.get("FailedEntryCount", 0)
    if failed > 0:
        for err_entry in response.get("Entries", []):
            if "ErrorCode" in err_entry or "ErrorMessage" in err_entry:
                logger.error(
                    "EventBridge batch entry failed",
                    extra={
                        "error_code": err_entry.get("ErrorCode"),
                        "error_message": err_entry.get("ErrorMessage"),
                    },
                )
    else:
        logger.info(
            "Published MCP event batch",
            extra={"entry_count": len(entries), "trace_ids": [m.trace_id for m in messages[:10]]},
        )

    return response
