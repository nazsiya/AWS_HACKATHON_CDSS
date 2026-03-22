"""
SQLAlchemy models for CDSS (Aurora PostgreSQL).

The models are aligned to the requirements for role-based access control,
comprehensive patient management, surgical workflow, and AI agent coordination.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.utcnow()


# Use portable JSON type for SQLite/local tests; use JSONB on PostgreSQL/Aurora.
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class User(Base):
    """Core Identity & Access Control - Requirement 1."""
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # doctor|patient|admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    doctor_profile: Mapped[Doctor | None] = relationship(back_populates="user", cascade="all,delete-orphan")
    patient_profile: Mapped[Patient | None] = relationship(back_populates="user", cascade="all,delete-orphan")


class Doctor(Base):
    """Doctor profiles - Requirement 1."""
    __tablename__ = "doctors"

    doctor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hospital_id: Mapped[str | None] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)  # available|busy|on_call|unavailable
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="doctor_profile")
    visits: Mapped[list[Visit]] = relationship(back_populates="doctor")
    surgeries: Mapped[list[Surgery]] = relationship(back_populates="surgeon")


class AuditLog(Base):
    """System-wide audit logs - Requirement 1 & 10."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(512), nullable=False)
    resource: Mapped[str] = mapped_column(String(512), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Consent(Base):
    """Patient consent management - Requirement 2 & Challenge 3."""
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)  # data_sharing|ai_processing|abdm_link
    purpose: Mapped[str | None] = mapped_column(String(512), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="consents")


class Patient(Base):
    """Comprehensive patient profiles - Requirement 2."""
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # PT-1001
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    abha_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    blood_group: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ward: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vitals: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    surgery_readiness: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    address_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    emergency_contact_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    last_visit: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    user: Mapped[User | None] = relationship(back_populates="patient_profile")
    visits: Mapped[list[Visit]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    surgeries: Mapped[list[Surgery]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    medications: Mapped[list[Medication]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    reminders: Mapped[list[Reminder]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    consents: Mapped[list[Consent]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    conditions: Mapped[list[MedicalCondition]] = relationship(back_populates="patient", cascade="all,delete-orphan")
    allergies: Mapped[list[Allergy]] = relationship(back_populates="patient", cascade="all,delete-orphan")


class MedicalCondition(Base):
    """Patient medical conditions - Requirement 2."""
    __tablename__ = "medical_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    condition_name: Mapped[str] = mapped_column(String(256), nullable=False)
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|resolved

    patient: Mapped[Patient] = relationship(back_populates="conditions")


class Allergy(Base):
    """Patient allergies - Requirement 2."""
    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    allergen: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="allergies")


class Visit(Base):
    """Patient consultations - Requirement 6."""
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=False)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    transcript_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="visits")
    doctor: Mapped[Doctor] = relationship(back_populates="visits")


class Surgery(Base):
    """Intelligent surgical workflow - Requirement 3."""
    __tablename__ = "surgeries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # SRG-1001
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    surgeon_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    ot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    scheduled_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)  # scheduled|completed|cancelled|in_progress
    checklist: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_TYPE, nullable=True)
    requirements_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="surgeries")
    surgeon: Mapped[Doctor] = relationship(back_populates="surgeries")
    team_members: Mapped[list[SurgicalTeamMember]] = relationship(back_populates="surgery", cascade="all,delete-orphan")
    requirements: Mapped[list[SurgeryRequirement]] = relationship(back_populates="surgery", cascade="all,delete-orphan")


class SurgeryRequirement(Base):
    """Specific requirements for a surgery - Requirement 3."""
    __tablename__ = "surgery_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surgery_id: Mapped[str] = mapped_column(ForeignKey("surgeries.id", ondelete="CASCADE"), nullable=False)
    instrument_name: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity_required: Mapped[int] = mapped_column(Integer, default=1)

    surgery: Mapped[Surgery] = relationship(back_populates="requirements")


class SurgicalTeamMember(Base):
    """Surgical team roles and specialists - Requirement 3."""
    __tablename__ = "surgical_team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surgery_id: Mapped[str] = mapped_column(ForeignKey("surgeries.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)  # surgeon|assistant|anesthetist|scrub_nurse

    surgery: Mapped[Surgery] = relationship(back_populates="team_members")


class Resource(Base):
    """Hospital resources - Requirement 4."""
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # ot|equipment|staff
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)
    availability: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class ResourceStatusLog(Base):
    """Real-time status tracking for resources - Requirement 4."""
    __tablename__ = "resource_status_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)  # doctor|equipment|ot
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class ScheduleSlot(Base):
    """Surgical scheduling - Requirement 5."""
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    slot_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    surgery_id: Mapped[str | None] = mapped_column(ForeignKey("surgeries.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="available", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class DoctorReplacement(Base):
    """Intelligent doctor replacement - Requirement 5."""
    __tablename__ = "doctor_replacements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surgery_id: Mapped[str] = mapped_column(ForeignKey("surgeries.id", ondelete="CASCADE"), nullable=False)
    original_doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=False)
    replacement_doctor_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class Conversation(Base):
    """AI Conversation Analysis - Requirement 6 & 7."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    summary: Mapped[ConversationSummary | None] = relationship(back_populates="conversation", cascade="all,delete-orphan")


class ConversationSummary(Base):
    """AI-powered conversation summaries - Requirement 6."""
    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="summary")


class Medication(Base):
    """Prescribed medications - Requirement 6."""
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    medication_name: Mapped[str] = mapped_column(String(256), nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_dose_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="medications")


class Reminder(Base):
    """Medication reminders - Requirement 6."""
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    medication_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)  # SMS|APP|CALL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="reminders")
    adherence_logs: Mapped[list[MedicationAdherenceLog]] = relationship(back_populates="reminder", cascade="all,delete-orphan")


class MedicationAdherenceLog(Base):
    """Tracking patient medication adherence - Requirement 6."""
    __tablename__ = "medication_adherence_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reminder_id: Mapped[int] = mapped_column(ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False)
    taken: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)

    reminder: Mapped[Reminder] = relationship(back_populates="adherence_logs")


class LanguageTranslation(Base):
    """Multilingual cache - Requirement 7."""
    __tablename__ = "language_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(32), nullable=False)
    target_language: Mapped[str] = mapped_column(String(32), nullable=False)


class Hospital(Base):
    """Hospital registry - Challenge 6."""
    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specialties: Mapped[list[str] | None] = mapped_column(JSON_TYPE, nullable=True)
    available_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    icu_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_icu_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)


class Notification(Base):
    """Real-time notifications and alerts - Requirement 9."""
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="INFO")  # INFO|WARNING|CRITICAL
    channel: Mapped[str] = mapped_column(String(32), default="APP")  # APP|SMS|EMAIL
    status: Mapped[str] = mapped_column(String(32), default="sent")  # sent|acknowledged
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class AlertLog(Base):
    """Historical record of clinical alerts - Requirement 9."""
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # critical|high|medium|low
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False) # drug_interaction|critical_vitals|...
    channel: Mapped[str] = mapped_column(String(32), nullable=False)   # doctor|pharmacist|emergency
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    doctor_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.doctor_id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class EscalationLog(Base):
    """Escalation events and acknowledgment tracking - Requirement 5.3."""
    __tablename__ = "escalation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alert_log.alert_id"), nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1, 2, 3
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # APP, EMAIL, SMS, VOICE
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    response_time_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AgentEvent(Base):
    """MCP agent-to-agent communication events - Requirement 8."""
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)


class AgentEventLog(Base):
    """Inter-agent event log for auditing - Requirement 8."""
    __tablename__ = "agent_event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    target_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_utcnow, nullable=False)
