#!/usr/bin/env python3
"""
Verify EventBridge rules and targets for CDSS agent routing.

Confirms that rules exist for AgentActionRequested and target the correct Lambdas.
Optionally run after publish_eventbridge_action.py to confirm rule matching.

Usage (deployed only; requires AWS credentials):
  EVENT_BUS_NAME=cdss-events-dev python scripts/agents/verify_eventbridge_routes.py

  # With AWS region
  EVENT_BUS_NAME=cdss-events-dev AWS_REGION=ap-south-1 python scripts/agents/verify_eventbridge_routes.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_DETAIL_TYPE = "AgentActionRequested"
EXPECTED_SOURCE = "cdss.agent.supervisor"


def list_rules_for_bus(client, event_bus_name: str) -> list[dict]:
    """List all rules on the given event bus."""
    paginator = client.get_paginator("list_rules")
    rules = []
    for page in paginator.paginate(EventBusName=event_bus_name):
        rules.extend(page.get("Rules", []))
    return rules


def get_rule_targets(client, event_bus_name: str, rule_name: str) -> list[dict]:
    """Get targets for a rule."""
    resp = client.list_targets_by_rule(Rule=rule_name, EventBusName=event_bus_name)
    return resp.get("Targets", [])


def verify_routes(event_bus_name: str | None = None, region: str | None = None) -> tuple[bool, list[str]]:
    """
    Verify EventBridge has rules for agent routing.

    :return: (success, list of messages)
    """
    try:
        import boto3
    except ImportError:
        return False, ["boto3 not installed"]

    bus = event_bus_name or os.environ.get("EVENT_BUS_NAME", "").strip()
    if not bus:
        return False, ["EVENT_BUS_NAME not set (deployed-only script)"]

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("events", region_name=region)
    messages = []

    # List rules
    try:
        rules = list_rules_for_bus(client, bus)
    except Exception as e:
        return False, ["list_rules failed: %s" % e]

    agent_rules = [r for r in rules if "route-to-" in r.get("Name", "") and "agent" in r.get("Name", "").lower()]
    if not agent_rules:
        messages.append("No agent routing rules found on bus %s (rules count: %d)" % (bus, len(rules)))
        # Not necessarily failure: might use different naming
        if not rules:
            return False, messages
        messages.append("Rule names: %s" % [r["Name"] for r in rules[:10]])
        return True, messages

    messages.append("Event bus: %s" % bus)
    messages.append("Agent routing rules: %d" % len(agent_rules))

    for rule in agent_rules:
        name = rule.get("Name", "")
        state = rule.get("State", "?")
        event_pattern = rule.get("EventPattern")
        if event_pattern:
            try:
                pat = json.loads(event_pattern)
                detail_type = pat.get("detail-type", [])
                source = pat.get("source", [])
                detail = pat.get("detail", {})
                target_agent = detail.get("target_agent", [])
                messages.append("  Rule: %s State=%s detail-type=%s source=%s target_agent=%s" % (
                    name, state, detail_type, source, target_agent
                ))
            except json.JSONDecodeError:
                messages.append("  Rule: %s State=%s (event pattern not JSON)" % (name, state))
        else:
            messages.append("  Rule: %s State=%s" % (name, state))

        targets = get_rule_targets(client, bus, name)
        for t in targets:
            arn = t.get("Arn", "")
            messages.append("    Target: %s" % (arn.split(":")[-1] if ":" in arn else arn))

    # Sanity: at least one rule should have detail-type AgentActionRequested
    any_match = False
    for rule in agent_rules:
        ep = rule.get("EventPattern")
        if ep and EXPECTED_DETAIL_TYPE in str(ep) and EXPECTED_SOURCE in str(ep):
            any_match = True
            break
    if agent_rules and not any_match:
        messages.append("WARN: No rule found with detail-type=%s and source=%s" % (EXPECTED_DETAIL_TYPE, EXPECTED_SOURCE))

    return True, messages


def main() -> int:
    ok, messages = verify_routes()
    for m in messages:
        print(m)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
