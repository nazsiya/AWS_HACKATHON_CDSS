#!/usr/bin/env python3
"""
Put MCP-shaped events to EventBridge for async SQS consumption.

Events use source "cdss.agents" so they are routed by infrastructure/notifications.tf
to the agent_events SQS queue and consumed by the MCP consumer Lambda.

Usage (deployed only; requires AWS credentials and EVENT_BUS_NAME):
  EVENT_BUS_NAME=cdss-events-dev python scripts/async/put_eventbridge_event.py patient_profile_request '{"patient_id":"PT-1001"}'
  EVENT_BUS_NAME=cdss-events-dev python scripts/async/put_eventbridge_event.py resource_availability_request '{"resource_type":"ot","date_from":"2025-03-01","date_to":"2025-03-07"}'

Detail types: patient_profile_request, surgery_requirements_request, resource_availability_request,
  schedule_optimization_request, conversation_summary_request, medication_reminder_request
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cdss.mcp.schemas import (
    DETAIL_TYPE_CONVERSATION_SUMMARY,
    DETAIL_TYPE_MEDICATION_REMINDER,
    DETAIL_TYPE_PATIENT_PROFILE,
    DETAIL_TYPE_RESOURCE_AVAILABILITY,
    DETAIL_TYPE_SCHEDULE_OPTIMIZATION,
    DETAIL_TYPE_SURGERY_REQUIREMENTS,
    DETAIL_TYPES,
    ConversationSummaryRequestPayload,
    MedicationReminderRequestPayload,
    PatientProfileRequestPayload,
    ResourceAvailabilityRequestPayload,
    ScheduleOptimizationRequestPayload,
    SurgeryRequirementsRequestPayload,
)


def build_detail(detail_type: str, payload_json: dict) -> dict:
    """Build EventBridge detail dict (MCP message) for the given detail_type and payload."""
    message_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    source_agent = "supervisor"
    target_agent = {
        DETAIL_TYPE_PATIENT_PROFILE: "patient",
        DETAIL_TYPE_SURGERY_REQUIREMENTS: "surgery",
        DETAIL_TYPE_RESOURCE_AVAILABILITY: "resource",
        DETAIL_TYPE_SCHEDULE_OPTIMIZATION: "scheduling",
        DETAIL_TYPE_CONVERSATION_SUMMARY: "engagement",
        DETAIL_TYPE_MEDICATION_REMINDER: "engagement",
    }.get(detail_type, "patient")

    payload_map = {
        DETAIL_TYPE_PATIENT_PROFILE: PatientProfileRequestPayload,
        DETAIL_TYPE_SURGERY_REQUIREMENTS: SurgeryRequirementsRequestPayload,
        DETAIL_TYPE_RESOURCE_AVAILABILITY: ResourceAvailabilityRequestPayload,
        DETAIL_TYPE_SCHEDULE_OPTIMIZATION: ScheduleOptimizationRequestPayload,
        DETAIL_TYPE_CONVERSATION_SUMMARY: ConversationSummaryRequestPayload,
        DETAIL_TYPE_MEDICATION_REMINDER: MedicationReminderRequestPayload,
    }
    payload_cls = payload_map.get(detail_type)
    if not payload_cls:
        raise ValueError("Unknown detail_type: %s; allowed: %s" % (detail_type, list(DETAIL_TYPES)))
    payload = payload_cls.model_validate(payload_json)

    detail = {
        "message_id": message_id,
        "trace_id": trace_id,
        "source_agent": source_agent,
        "target_agent": target_agent,
        "payload": payload.model_dump(mode="json"),
    }
    return detail


def put_mcp_event(
    detail_type: str,
    payload: dict,
    event_bus_name: str | None = None,
    region: str | None = None,
) -> dict:
    """
    Put one MCP event to the CDSS event bus (source cdss.agents).

    Event is routed to SQS agent_events by the inter_agent_messaging rule.
    """
    import boto3

    bus = event_bus_name or os.environ.get("EVENT_BUS_NAME", "").strip()
    if not bus:
        raise ValueError("EVENT_BUS_NAME must be set (e.g. from Terraform output cdss_event_bus_name)")

    if detail_type not in DETAIL_TYPES:
        raise ValueError("detail_type must be one of %s" % list(DETAIL_TYPES))

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("events", region_name=region)
    detail = build_detail(detail_type, payload)

    entry = {
        "Source": "cdss.agents",
        "DetailType": detail_type,
        "Detail": json.dumps(detail),
        "EventBusName": bus,
    }
    resp = client.put_events(Entries=[entry])
    return resp


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: put_eventbridge_event.py <detail_type> <payload_json>", file=sys.stderr)
        print("  detail_type: one of %s" % list(DETAIL_TYPES), file=sys.stderr)
        print("  payload_json: e.g. '{\"patient_id\":\"PT-1001\"}'", file=sys.stderr)
        print("  Set EVENT_BUS_NAME to your event bus name (Terraform: cdss_event_bus_name)", file=sys.stderr)
        return 2

    detail_type = sys.argv[1].strip()
    payload_str = sys.argv[2]
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print("Invalid payload_json: %s" % e, file=sys.stderr)
        return 2

    if not os.environ.get("EVENT_BUS_NAME"):
        print("EVENT_BUS_NAME is not set. Deployed-only script.", file=sys.stderr)
        return 1

    try:
        resp = put_mcp_event(detail_type, payload)
    except Exception as e:
        print("Put events failed: %s" % e, file=sys.stderr)
        return 1

    failed = resp.get("FailedEntryCount", 0)
    entries = resp.get("Entries", [])
    if failed or not entries:
        print("Failed to put event: %s" % resp, file=sys.stderr)
        return 1
    if entries[0].get("EventId"):
        print("EventId: %s" % entries[0]["EventId"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
