"""Resource and scheduling models (OT, equipment, slots)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OTSlot(BaseModel):
    """OT availability slot."""

    ot_id: str
    start: datetime
    end: datetime
    available: bool = True


class BookSlotRequest(BaseModel):
    """Request to book a slot (appointment or OT)."""

    slot_type: str  # appointment | ot
    entity_id: str  # patient_id or procedure_id
    start: datetime
    end: datetime
    ot_id: Optional[str] = None
