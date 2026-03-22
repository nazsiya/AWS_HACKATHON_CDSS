"""
SQS consumer for MCP inter-agent messages (async path).

Triggered by agent_events SQS when EventBridge forwards events from source "cdss.agents".
Parses EventBridge envelope from SQS body, routes by DetailType to agent processors,
and ensures on failure: message is not deleted (so SQS retries then DLQ), with trace_id
logged for audit and DLQ inspection.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cdss.mcp.schemas import (
    DETAIL_TYPE_TO_MODEL,
    BaseMCPMessage,
)

logger = logging.getLogger(__name__)

# EventBridge envelope keys when event is delivered to SQS (body is full event JSON)
EVENTBRIDGE_DETAIL_TYPE = "detail-type"
EVENTBRIDGE_DETAIL = "detail"


def _parse_eventbridge_body(body: str) -> tuple[str, dict[str, Any]]:
    """
    Parse SQS message body as EventBridge event. Returns (detail_type, detail_dict).

    EventBridge sends the full event to SQS; detail may be JSON string or already dict.
    """
    envelope = json.loads(body)
    detail_type = envelope.get(EVENTBRIDGE_DETAIL_TYPE) or ""
    detail_raw = envelope.get(EVENTBRIDGE_DETAIL)
    if detail_raw is None:
        raise ValueError("EventBridge event missing 'detail'")
    if isinstance(detail_raw, str):
        detail = json.loads(detail_raw)
    else:
        detail = detail_raw
    if not isinstance(detail, dict):
        raise ValueError("EventBridge 'detail' must be JSON object or JSON string")
    return detail_type, detail


def _parse_mcp_message(detail_type: str, detail: dict[str, Any]) -> BaseMCPMessage:
    """Validate and parse detail into the MCP request model for detail_type."""
    model_cls = DETAIL_TYPE_TO_MODEL.get(detail_type)
    if model_cls is None:
        raise ValueError(f"Unknown MCP detail_type: {detail_type}")
    return model_cls.model_validate(detail)


def _process_patient_profile(msg: BaseMCPMessage) -> None:
    """Handle patient_profile_request. Stub: log and optionally call patient agent later."""
    logger.info(
        "MCP consume patient_profile_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )
    # TODO: call patient agent logic (e.g. load from Aurora, optional Bedrock), write results


def _process_surgery_requirements(msg: BaseMCPMessage) -> None:
    """Handle surgery_requirements_request. Stub: log and optionally call surgery agent."""
    logger.info(
        "MCP consume surgery_requirements_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )


def _process_resource_availability(msg: BaseMCPMessage) -> None:
    """Handle resource_availability_request. Stub: log and optionally call resource agent."""
    logger.info(
        "MCP consume resource_availability_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )


def _process_schedule_optimization(msg: BaseMCPMessage) -> None:
    """Handle schedule_optimization_request. Stub: log and optionally call scheduling agent."""
    logger.info(
        "MCP consume schedule_optimization_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )


def _process_conversation_summary(msg: BaseMCPMessage) -> None:
    """Handle conversation_summary_request. Stub: log and optionally call engagement agent."""
    logger.info(
        "MCP consume conversation_summary_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )


def _process_medication_reminder(msg: BaseMCPMessage) -> None:
    """Handle medication_reminder_request. Stub: log and optionally call engagement agent."""
    logger.info(
        "MCP consume medication_reminder_request",
        extra={"trace_id": msg.trace_id, "target_agent": msg.target_agent},
    )


_ROUTER: dict[str, Any] = {
    "patient_profile_request": _process_patient_profile,
    "surgery_requirements_request": _process_surgery_requirements,
    "resource_availability_request": _process_resource_availability,
    "schedule_optimization_request": _process_schedule_optimization,
    "conversation_summary_request": _process_conversation_summary,
    "medication_reminder_request": _process_medication_reminder,
}


def _route_and_process(detail_type: str, detail: dict[str, Any]) -> None:
    """Parse message, route by detail_type, and run the processor. Raises on error."""
    msg = _parse_mcp_message(detail_type, detail)
    processor = _ROUTER.get(detail_type)
    if processor is None:
        raise ValueError(f"No processor for detail_type: {detail_type}")
    processor(msg)


def _process_record(record: dict[str, Any]) -> None:
    """
    Process one SQS record (EventBridge event in body). Raises on parse or process failure.

    On exception, caller should log trace_id (from detail if available) and re-raise
    so Lambda fails and SQS does not delete the message; after maxReceiveCount it goes to DLQ.
    """
    body = record.get("body")
    if not body:
        raise ValueError("SQS record missing body")
    detail_type, detail = _parse_eventbridge_body(body)
    trace_id = detail.get("trace_id", "unknown")
    try:
        _route_and_process(detail_type, detail)
    except Exception:
        logger.error(
            "MCP consumer processing failed; message will retry then DLQ",
            extra={"trace_id": trace_id, "detail_type": detail_type},
            exc_info=True,
        )
        raise


def handler(event: dict[str, Any], context: Any) -> None:
    """
    Lambda entrypoint for SQS-triggered agent_events consumption.

    Processes each SQS record (EventBridge event). On any record failure, logs
    trace_id and re-raises so the batch is not fully deleted and failed messages
    retry (SQS visibility timeout) and after maxReceiveCount move to DLQ. The
    DLQ message body retains the full EventBridge event including detail.trace_id
    for audit and inspection.
    """
    records = event.get("Records") or []
    for record in records:
        _process_record(record)
