"""
Patient Agent API handler.
History retrieval, RAG summaries, create/update patient, getSummary.
"""

import json
from typing import Any

from cdss.agents.patient_agent import PatientAgent


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entrypoint for Patient Agent."""
    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "getSummary")
    payload = body.get("payload", {})

    agent = PatientAgent()
    actions = {
        "getHistory": agent.get_history,
        "getRAGSummary": agent.get_rag_summary,
        "createPatient": agent.create_patient,
        "getSummary": agent.get_summary,
        "updateRecord": agent.update_record,
    }
    fn = actions.get(action, agent.get_summary)
    result = fn(payload)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }
