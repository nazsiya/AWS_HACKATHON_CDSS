#!/usr/bin/env python3
"""
Emit AgentActionRequested events to EventBridge for async agent invocation.

Event shape matches infrastructure/modules/eventbridge/main.tf:
  source      = "cdss.agent.supervisor"
  detail-type = "AgentActionRequested"
  detail      = { target_agent, action, params, session_id, event_type, ... }

Usage (deployed only; requires AWS credentials and EVENT_BUS_NAME):
  EVENT_BUS_NAME=cdss-events-dev python scripts/agents/publish_eventbridge_action.py patient get_patient_summary '{"patient_id":"PT-1001"}'

  # With optional session_id
  EVENT_BUS_NAME=cdss-events-dev SESSION_ID=SESS-001 python scripts/agents/publish_eventbridge_action.py scheduling book_slot '{"slot_id":"SLOT-1"}'
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# EventBridge expects target_agent to match rule filter (patient, surgery, resource, scheduling, engagement)
TARGET_AGENTS = {"patient", "surgery", "resource", "scheduling", "engagement"}


def put_agent_action(
    target_agent: str,
    action: str,
    params: dict,
    session_id: str | None = None,
    event_bus_name: str | None = None,
    region: str | None = None,
) -> dict:
    """
    Put one AgentActionRequested event to the CDSS event bus.

    :param target_agent: One of patient, surgery, resource, scheduling, engagement
    :param action: Action name (e.g. get_patient_summary, book_slot)
    :param params: Dict of parameters (e.g. {"patient_id": "PT-1001"})
    :param session_id: Optional session id for audit
    :param event_bus_name: Event bus name (default from EVENT_BUS_NAME env)
    :param region: AWS region (default from AWS_REGION or ap-south-1)
    :return: put_events response
    """
    import boto3

    bus = event_bus_name or os.environ.get("EVENT_BUS_NAME", "").strip()
    if not bus:
        raise ValueError("EVENT_BUS_NAME must be set (e.g. from Terraform output cdss_event_bus_name)")

    if target_agent not in TARGET_AGENTS:
        raise ValueError("target_agent must be one of %s" % sorted(TARGET_AGENTS))

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("events", region_name=region)

    detail = {
        "event_type": "AgentActionRequested",
        "target_agent": target_agent,
        "action": action,
        "params": params,
    }
    if session_id:
        detail["session_id"] = session_id

    entry = {
        "Source": "cdss.agent.supervisor",
        "DetailType": "AgentActionRequested",
        "Detail": json.dumps(detail),
        "EventBusName": bus,
    }

    resp = client.put_events(Entries=[entry])
    return resp


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: publish_eventbridge_action.py <target_agent> <action> <params_json> [session_id]", file=sys.stderr)
        print("  target_agent: patient | surgery | resource | scheduling | engagement", file=sys.stderr)
        print("  action: e.g. get_patient_summary, book_slot", file=sys.stderr)
        print("  params_json: e.g. '{\"patient_id\":\"PT-1001\"}'", file=sys.stderr)
        print("  Set EVENT_BUS_NAME to your event bus name (Terraform: cdss_event_bus_name)", file=sys.stderr)
        return 2

    target_agent = sys.argv[1].strip().lower()
    action = sys.argv[2].strip()
    params_str = sys.argv[3]
    session_id = sys.argv[4].strip() if len(sys.argv) > 4 else os.environ.get("SESSION_ID")

    try:
        params = json.loads(params_str)
    except json.JSONDecodeError as e:
        print("Invalid params_json: %s" % e, file=sys.stderr)
        return 2

    if not os.environ.get("EVENT_BUS_NAME"):
        print("EVENT_BUS_NAME is not set. Deployed-only script.", file=sys.stderr)
        return 1

    try:
        resp = put_agent_action(target_agent, action, params, session_id=session_id)
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
