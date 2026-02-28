"""Patient domain models (RDS, ABDM alignment)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    """Payload for creating a patient record."""

    name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    abha_id: Optional[str] = Field(None, description="ABDM Health ID")
    mobile: Optional[str] = None
    language_preference: str = "en"


class PatientUpdate(BaseModel):
    """Payload for updating patient record."""

    name: Optional[str] = None
    mobile: Optional[str] = None
    language_preference: Optional[str] = None


class PatientSummary(BaseModel):
    """Patient summary for RAG/UI."""

    patient_id: str
    summary_text: str
    last_consultation: Optional[str] = None
    active_medications: list[str] = []
