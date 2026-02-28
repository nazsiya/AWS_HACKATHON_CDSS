"""Surgery planning models (OT checklist, protocols)."""

from typing import Any, Optional

from pydantic import BaseModel


class SurgeryPlan(BaseModel):
    """Surgery plan input for analysis."""

    surgery_type: str
    patient_id: Optional[str] = None
    proposed_date: Optional[str] = None
    notes: Optional[str] = None
    metadata: dict[str, Any] = {}


class ChecklistItem(BaseModel):
    """Single checklist item."""

    step: int
    description: str
    category: str = "general"
    required: bool = True
