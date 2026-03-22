"""
Pydantic schemas for CDSS clinical assessments.

Per CDSS.mdc: All AI-generated clinical assessments must use strict, versioned
schemas and be validated with Pydantic before use.

Per bedrock-agents.mdc: Prefer tool use with strict input_schema; map tool
inputs to Pydantic models, validate, then execute business logic.

Per project-conventions.mdc: Validate and normalize all model outputs via
strict schemas before use. AI is doctor-in-the-loop.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ClinicalAssessment(BaseModel):
    """
    Patient risk / priority assessment per CDSS.mdc.

    If confidence < 0.85 or required data is missing:
      - priority must be at least 'high'
      - requires_senior_review must be True
    """

    patient_id: str
    priority: Literal["critical", "high", "medium", "low"]
    confidence: float = Field(ge=0.0, le=1.0, description="0.0–1.0 confidence score")
    risk_factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    requires_senior_review: bool = False
    safety_disclaimer: str = (
        "AI is for clinical support only. All decisions require qualified "
        "medical judgment. This system does not replace a doctor."
    )

    @model_validator(mode="after")
    def enforce_safety_rules(self) -> "ClinicalAssessment":
        """CDSS.mdc: If confidence < 0.85 → escalate."""
        if self.confidence < 0.85:
            if self.priority not in ("critical", "high"):
                self.priority = "high"
            self.requires_senior_review = True
        return self


class SurgeryReadiness(BaseModel):
    """
    Surgery readiness assessment per CDSS.mdc.

    Includes pre_op_status, risk_factors, checklist_flags,
    and requires_senior_review.
    """

    patient_id: str
    surgery_id: str = ""
    pre_op_status: Literal["pending", "in_progress", "cleared", "on_hold"] = "pending"
    risk_factors: list[str] = Field(default_factory=list, description="Plain language + coded where available")
    checklist_flags: list[str] = Field(
        default_factory=list,
        description="e.g. 'labs pending', 'NPO not confirmed'",
    )
    requires_senior_review: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    safety_disclaimer: str = (
        "Surgery readiness is for clinical decision support only. "
        "Final clearance must be given by the treating clinician."
    )

    @model_validator(mode="after")
    def enforce_safety_rules(self) -> "SurgeryReadiness":
        """CDSS.mdc: escalate when confidence is low or data incomplete."""
        if self.confidence < 0.85:
            self.requires_senior_review = True
        if self.checklist_flags:
            self.requires_senior_review = True
        return self


class PatientSummaryResponse(BaseModel):
    """Validated response from Bedrock patient summary generation."""

    patient_id: str
    summary: str
    key_conditions: list[str] = Field(default_factory=list)
    active_medications: list[str] = Field(default_factory=list)
    upcoming_surgeries: list[str] = Field(default_factory=list)
    risk_level: Literal["critical", "high", "medium", "low"] = "medium"
    safety_disclaimer: str = (
        "AI-generated summary. Always verify with the patient's full medical record."
    )


class AlertPayload(BaseModel):
    """Schema for alert engine payloads (Req 9)."""

    severity: Literal["critical", "high", "medium", "low"]
    alert_type: str = Field(description="e.g. drug_interaction, critical_vitals, surgical_complication, non_adherence")
    channel: str = Field(default="doctor", description="Target: doctor, pharmacist, emergency")
    patient_id: str = ""
    doctor_id: str = ""
    message: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    safety_disclaimer: str = "Clinical alert for decision support only."
