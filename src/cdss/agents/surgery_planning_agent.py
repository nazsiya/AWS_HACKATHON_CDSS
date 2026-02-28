"""
Surgery Planning Agent: OT checklists, protocols, analyseSurgery, generateChecklist.
Uses Clinical Protocols MCP, Hospital Systems MCP.
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class SurgeryPlanningAgent(BaseAgent):
    """Manages OT checklists, surgical protocols, and analysis."""

    name = "SurgeryPlanningAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "getOTChecklists", "description": "Get operation theatre checklists"},
            {"name": "getProtocols", "description": "Get surgical protocols"},
            {"name": "analyseSurgery", "description": "Analyse surgery plan"},
            {"name": "generateChecklist", "description": "Generate surgical checklist"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Surgery Planning Agent for an Indian hospital. "
            "You manage OT checklists, protocols, and generate evidence-based checklists. "
            "Uses Clinical Protocols MCP for drug interactions and evidence DB."
        )

    def get_ot_checklists(self, payload: dict[str, Any]) -> dict[str, Any]:
        """OT checklists for given surgery type."""
        surgery_type = payload.get("surgeryType", "")
        return {"surgeryType": surgery_type, "checklists": []}

    def get_protocols(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Surgical protocols from Clinical Protocols MCP."""
        return {"protocols": [], "source": "ClinicalProtocolsMCP"}

    def analyse_surgery(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyse surgery plan (risk, equipment, timeline)."""
        plan = payload.get("plan", {})
        return {"analysis": {}, "plan": plan}

    def generate_checklist(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate surgical checklist from protocol + plan."""
        surgery_type = payload.get("surgeryType", "")
        return {"surgeryType": surgery_type, "checklist": [], "generated": True}
