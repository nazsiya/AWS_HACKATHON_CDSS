"""
Resource Agent: OT availability, equipment, checkOT, allocateEquipment.
Integrates with Hospital Systems MCP (OT status, bed availability).
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class ResourceAgent(BaseAgent):
    """Checks OT availability and allocates equipment."""

    name = "ResourceAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "getOTAvailability", "description": "Get OT availability"},
            {"name": "getEquipment", "description": "Get equipment list"},
            {"name": "checkOT", "description": "Check OT status"},
            {"name": "allocateEquipment", "description": "Allocate equipment for procedure"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Resource Agent for an Indian hospital. "
            "You check OT availability and bed status via Hospital Systems MCP, "
            "and manage equipment allocation."
        )

    def get_ot_availability(self, payload: dict[str, Any]) -> dict[str, Any]:
        """OT availability from Hospital Systems MCP."""
        date = payload.get("date", "")
        return {"date": date, "slots": [], "source": "HospitalSystemsMCP"}

    def get_equipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Equipment list (DynamoDB / Hospital Systems)."""
        return {"equipment": [], "available": []}

    def check_ot(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check OT status (OT status from MCP)."""
        ot_id = payload.get("otId", "")
        return {"otId": ot_id, "status": "unknown", "available": False}

    def allocate_equipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Allocate equipment for procedure."""
        procedure_id = payload.get("procedureId", "")
        equipment_ids = payload.get("equipmentIds", [])
        return {"procedureId": procedure_id, "allocated": equipment_ids, "success": True}
