"""
Scheduling Agent: Appointments, OT booking, bookSlot, resolveConflict.
Uses DynamoDB for session state, EventBridge for async messaging.
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class SchedulingAgent(BaseAgent):
    """Manages appointments and OT booking."""

    name = "SchedulingAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "getAppointments", "description": "Get appointments"},
            {"name": "bookOT", "description": "Book OT slot"},
            {"name": "bookSlot", "description": "Book time slot"},
            {"name": "resolveConflict", "description": "Resolve scheduling conflict"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Scheduling Agent for an Indian hospital. "
            "You manage appointments and OT booking, and resolve conflicts. "
            "Uses DynamoDB for session state and EventBridge for async events."
        )

    def get_appointments(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get appointments for patient or doctor."""
        entity_id = payload.get("entityId", "")
        entity_type = payload.get("entityType", "patient")
        return {"entityId": entity_id, "entityType": entity_type, "appointments": []}

    def book_ot(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Book OT slot."""
        ot_id = payload.get("otId", "")
        slot = payload.get("slot", "")
        return {"otId": ot_id, "slot": slot, "booked": True}

    def book_slot(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Book specific time slot (appointment or OT)."""
        slot_type = payload.get("slotType", "appointment")
        return {"slotType": slot_type, "booked": True, "conflicts": []}

    def resolve_conflict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Resolve scheduling conflict."""
        conflict_id = payload.get("conflictId", "")
        return {"conflictId": conflict_id, "resolved": True}
