"""
MCP message schemas for inter-agent communication via EventBridge/SQS.

Versioned Pydantic models for request types used in cdss.agents event bus.
All messages include trace_id, source_agent, and target_agent for audit and routing.
Use these schemas for validation on publish and consume (see mcp/events.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Schema version for evolution; include in serialized payloads when needed
MCP_SCHEMA_VERSION = "1.0"

# Allowed agent identifiers (source/target)
AgentName = Literal[
    "patient",
    "surgery",
    "resource",
    "scheduling",
    "engagement",
    "supervisor",
]


class BaseMCPMessage(BaseModel):
    """Common fields for all MCP messages. Include in every EventBridge Detail."""

    message_id: str = Field(..., description="Unique id for idempotency and deduplication")
    trace_id: str = Field(..., description="Correlation id for audit and request tracing")
    source_agent: AgentName = Field(..., description="Agent sending the message")
    target_agent: AgentName = Field(..., description="Agent that should handle the message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reply_to: Optional[str] = Field(None, description="Optional queue or endpoint for async reply")

    model_config = {"extra": "forbid", "str_strip_whitespace": True}


# --- Payload models (typed per request) ---


class PatientProfileRequestPayload(BaseModel):
    """Payload for patient_profile_request. Scoped to a single patient."""

    patient_id: str = Field(..., description="Patient identifier (sensitive; do not log raw)")
    include_visits: bool = Field(True, description="Include visit/consultation history")
    include_abdm: bool = Field(False, description="Include ABDM/EHR fetch when enabled")

    model_config = {"extra": "forbid"}


class SurgeryRequirementsRequestPayload(BaseModel):
    """Payload for surgery_requirements_request."""

    surgery_id: Optional[str] = Field(None, description="Existing surgery record id")
    patient_id: Optional[str] = Field(None, description="Patient when surgery not yet created")
    surgery_type: Optional[str] = Field(None, description="Surgery type for requirement derivation")
    include_checklist: bool = Field(True, description="Include procedural checklist")

    model_config = {"extra": "forbid"}


class ResourceAvailabilityRequestPayload(BaseModel):
    """Payload for resource_availability_request."""

    resource_type: Literal["ot", "equipment", "staff"] = Field(
        ..., description="Type of resource to query"
    )
    date_from: Optional[str] = Field(None, description="Start date (ISO date) for availability")
    date_to: Optional[str] = Field(None, description="End date (ISO date) for availability")
    filters: Optional[dict[str, Any]] = Field(None, description="Optional type-specific filters")

    model_config = {"extra": "forbid"}


class ScheduleOptimizationRequestPayload(BaseModel):
    """Payload for schedule_optimization_request."""

    date_from: str = Field(..., description="Start date (ISO date) for schedule window")
    date_to: str = Field(..., description="End date (ISO date) for schedule window")
    surgery_ids: Optional[list[str]] = Field(None, description="Surgeries to place or adjust")
    constraints: Optional[dict[str, Any]] = Field(
        None, description="Optional constraints (e.g. priority, OT preferences)"
    )

    model_config = {"extra": "forbid"}


class ConversationSummaryRequestPayload(BaseModel):
    """Payload for conversation_summary_request (engagement agent)."""

    visit_id: Optional[str] = Field(None, description="Visit/consultation id")
    consultation_id: Optional[str] = Field(None, description="Consultation id if different from visit")
    patient_id: Optional[str] = Field(None, description="Patient context (sensitive)")
    transcript_ref: Optional[str] = Field(None, description="S3 key or ref to transcript when stored")

    model_config = {"extra": "forbid"}


class MedicationReminderRequestPayload(BaseModel):
    """Payload for medication_reminder_request."""

    action: Literal["create", "send", "cancel"] = Field(..., description="Reminder action")
    patient_id: str = Field(..., description="Patient identifier (sensitive)")
    reminder_id: Optional[str] = Field(None, description="Existing reminder id for send/cancel")
    medication_ids: Optional[list[str]] = Field(None, description="Medication ids for create")
    scheduled_at: Optional[str] = Field(None, description="ISO datetime for create")

    model_config = {"extra": "forbid"}


# --- Full request messages (base + payload) ---


class PatientProfileRequest(BaseMCPMessage):
    """MCP request: get patient profile. DetailType: patient_profile_request."""

    payload: PatientProfileRequestPayload


class SurgeryRequirementsRequest(BaseMCPMessage):
    """MCP request: get surgery requirements/checklist. DetailType: surgery_requirements_request."""

    payload: SurgeryRequirementsRequestPayload


class ResourceAvailabilityRequest(BaseMCPMessage):
    """MCP request: check resource availability. DetailType: resource_availability_request."""

    payload: ResourceAvailabilityRequestPayload


class ScheduleOptimizationRequest(BaseMCPMessage):
    """MCP request: optimize schedule. DetailType: schedule_optimization_request."""

    payload: ScheduleOptimizationRequestPayload


class ConversationSummaryRequest(BaseMCPMessage):
    """MCP request: summarize conversation. DetailType: conversation_summary_request."""

    payload: ConversationSummaryRequestPayload


class MedicationReminderRequest(BaseMCPMessage):
    """MCP request: create/send/cancel medication reminder. DetailType: medication_reminder_request."""

    payload: MedicationReminderRequestPayload


# Union for parsing by DetailType
MCPRequest = (
    PatientProfileRequest
    | SurgeryRequirementsRequest
    | ResourceAvailabilityRequest
    | ScheduleOptimizationRequest
    | ConversationSummaryRequest
    | MedicationReminderRequest
)

# DetailType values for EventBridge put_events (must match rule routing)
DETAIL_TYPE_PATIENT_PROFILE = "patient_profile_request"
DETAIL_TYPE_SURGERY_REQUIREMENTS = "surgery_requirements_request"
DETAIL_TYPE_RESOURCE_AVAILABILITY = "resource_availability_request"
DETAIL_TYPE_SCHEDULE_OPTIMIZATION = "schedule_optimization_request"
DETAIL_TYPE_CONVERSATION_SUMMARY = "conversation_summary_request"
DETAIL_TYPE_MEDICATION_REMINDER = "medication_reminder_request"

DETAIL_TYPES = (
    DETAIL_TYPE_PATIENT_PROFILE,
    DETAIL_TYPE_SURGERY_REQUIREMENTS,
    DETAIL_TYPE_RESOURCE_AVAILABILITY,
    DETAIL_TYPE_SCHEDULE_OPTIMIZATION,
    DETAIL_TYPE_CONVERSATION_SUMMARY,
    DETAIL_TYPE_MEDICATION_REMINDER,
)

# Map DetailType -> model class for deserialization
DETAIL_TYPE_TO_MODEL: dict[str, type[BaseMCPMessage]] = {
    DETAIL_TYPE_PATIENT_PROFILE: PatientProfileRequest,
    DETAIL_TYPE_SURGERY_REQUIREMENTS: SurgeryRequirementsRequest,
    DETAIL_TYPE_RESOURCE_AVAILABILITY: ResourceAvailabilityRequest,
    DETAIL_TYPE_SCHEDULE_OPTIMIZATION: ScheduleOptimizationRequest,
    DETAIL_TYPE_CONVERSATION_SUMMARY: ConversationSummaryRequest,
    DETAIL_TYPE_MEDICATION_REMINDER: MedicationReminderRequest,
}
