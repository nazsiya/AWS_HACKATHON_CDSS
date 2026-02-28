"""
Supervisor Agent: routes user intents to sub-agents and aggregates responses.
Orchestrates Patient, Surgery Planning, Resource, Scheduling, Engagement agents.
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.agents.engagement_agent import EngagementAgent
from cdss.agents.patient_agent import PatientAgent
from cdss.agents.resource_agent import ResourceAgent
from cdss.agents.scheduling_agent import SchedulingAgent
from cdss.agents.surgery_planning_agent import SurgeryPlanningAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)

INTENT_TO_AGENT = {
    "patient": "PatientAgent",
    "history": "PatientAgent",
    "summary": "PatientAgent",
    "surgery": "SurgeryPlanningAgent",
    "ot": "ResourceAgent",
    "resource": "ResourceAgent",
    "schedule": "SchedulingAgent",
    "appointment": "SchedulingAgent",
    "booking": "SchedulingAgent",
    "reminder": "EngagementAgent",
    "escalation": "EngagementAgent",
    "engagement": "EngagementAgent",
}


class SupervisorAgent(BaseAgent):
    """Routes intents and aggregates sub-agent responses."""

    name = "SupervisorAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "routeIntent", "description": "Route user intent to correct sub-agent"},
            {"name": "aggregateResponse", "description": "Aggregate responses from sub-agents"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Supervisor for an Indian hospital. "
            "Route user intents to: PatientAgent, SurgeryPlanningAgent, ResourceAgent, "
            "SchedulingAgent, or EngagementAgent. DISHA compliant."
        )

    def _get_agent(self, agent_name: str) -> BaseAgent:
        agents = {
            "PatientAgent": PatientAgent,
            "SurgeryPlanningAgent": SurgeryPlanningAgent,
            "ResourceAgent": ResourceAgent,
            "SchedulingAgent": SchedulingAgent,
            "EngagementAgent": EngagementAgent,
        }
        return agents.get(agent_name, PatientAgent)()

    def route_intent(self, intent: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Determine which sub-agent should handle the intent."""
        intent_lower = (intent or "").lower()
        agent_name = "PatientAgent"
        for keyword, name in INTENT_TO_AGENT.items():
            if keyword in intent_lower:
                agent_name = name
                break
        logger.info("route_intent", extra={"intent": intent, "agent": agent_name})
        return {"agent": agent_name, "payload": payload}

    def aggregate_response(self, responses: list[dict[str, Any]]) -> dict[str, Any]:
        """Combine sub-agent responses into a single reply."""
        return {"aggregated": True, "responses": responses, "summary": ""}
