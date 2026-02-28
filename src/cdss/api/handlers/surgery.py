"""
Surgery Planning Agent API handler.
OT checklists, protocols, analyseSurgery, generateChecklist.
"""

import json
from typing import Any

from cdss.agents.surgery_planning_agent import SurgeryPlanningAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for Surgery Planning Agent."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "generateChecklist")
    payload = body.get("payload", {})

    agent = SurgeryPlanningAgent()
    actions = {
        "getOTChecklists": agent.get_ot_checklists,
        "getProtocols": agent.get_protocols,
        "analyseSurgery": agent.analyse_surgery,
        "generateChecklist": agent.generate_checklist,
    }
    fn = actions.get(action, agent.generate_checklist)
    result = fn(payload)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
