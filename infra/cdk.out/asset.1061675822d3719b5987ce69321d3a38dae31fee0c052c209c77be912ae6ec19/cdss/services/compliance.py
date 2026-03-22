"""
Compliance and audit reporting helpers.

Phase 1–2: basic DISHA-aligned counts + CSV export for audit entries.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone


def get_compliance_dashboard() -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        from sqlalchemy import func, select

        from cdss.db.models import AuditLog, Patient
        from cdss.db.session import get_session

        with get_session() as session:
            total_audit = session.scalar(select(func.count(AuditLog.id))) or 0
            audit_today = session.scalar(select(func.count(AuditLog.id)).where(AuditLog.timestamp >= day_start)) or 0
            total_patients = session.scalar(select(func.count(Patient.id))) or 0
    except Exception:
        total_audit = 0
        audit_today = 0
        total_patients = 0

    return {
        "total_audit_entries": total_audit,
        "audit_entries_today": audit_today,
        "total_patients": total_patients,
        "patients_with_consent": 0,
        "consent_rate_percent": 0.0,
        "data_retention_status": "unknown",
        "oldest_record_age_days": 0,
        "retention_policy_days": 2555,  # ~7 years placeholder
        "compliance_score": 0.0,
    }


def generate_audit_report(date_from: date | None = None, date_to: date | None = None) -> str:
    """
    Return CSV for audit entries.
    """
    try:
        from sqlalchemy import select

        from cdss.db.models import AuditLog
        from cdss.db.session import get_session

        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc) if date_from else None
        end_dt = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc) if date_to else None

        with get_session() as session:
            stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
            if start_dt is not None:
                stmt = stmt.where(AuditLog.timestamp >= start_dt.replace(tzinfo=None))
            if end_dt is not None:
                stmt = stmt.where(AuditLog.timestamp <= end_dt.replace(tzinfo=None))
            rows = session.scalars(stmt).all()
    except Exception:
        rows = []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "timestamp", "user_id", "user_email", "action", "resource"])
    for r in rows:
        writer.writerow(
            [
                getattr(r, "id", ""),
                getattr(r, "timestamp", "") and getattr(r, "timestamp").isoformat(),
                getattr(r, "user_id", ""),
                getattr(r, "user_email", "") or "",
                getattr(r, "action", ""),
                getattr(r, "resource", ""),
            ]
        )
    return buf.getvalue()

"""
Compliance service for CDSS – DISHA audit reports, consent tracking, data retention.

Provides:
  - Audit report generation (CSV export from audit_log table)
  - Consent status tracking per patient
  - Data retention policy checks

Per CDSS.mdc: all data access is logged; patient consent is tracked for ABDM compliance.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, select

from cdss.db.models import AuditLog, Patient
from cdss.db.session import get_session

logger = logging.getLogger(__name__)

# Retention policy: days after which records should be archived
DATA_RETENTION_DAYS = 365 * 7  # 7 years per Indian medical records regulation


def generate_audit_report(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 10000,
) -> str:
    """
    Generate a DISHA-compliant audit report as CSV string.

    Includes: timestamp, user_id, user_email, action, resource.
    Returns CSV string ready for download.
    """
    with get_session() as session:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(min(limit, 50000))
        )
        if date_from:
            stmt = stmt.where(AuditLog.timestamp >= datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc))
        if date_to:
            stmt = stmt.where(AuditLog.timestamp <= datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc))

        rows = session.scalars(stmt).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "user_id", "user_email", "action", "resource"])
        for r in rows:
            writer.writerow([
                r.timestamp.isoformat() if r.timestamp else "",
                r.user_id or "",
                r.user_email or "",
                r.action or "",
                r.resource or "",
            ])
        return output.getvalue()


def get_compliance_dashboard() -> dict[str, Any]:
    """
    Return compliance metrics for the admin dashboard.

    Metrics:
      - total_audit_entries: total audit log records
      - audit_entries_today: entries in the last 24h
      - total_patients: total patient records
      - patients_with_consent: patients with consent records
      - data_retention_status: compliant / at_risk / overdue
      - oldest_record_age_days: age of oldest audit entry
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    with get_session() as session:
        # Audit metrics
        total_audit = session.scalar(select(func.count(AuditLog.id))) or 0
        audit_today = session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.timestamp >= today_start)
        ) or 0

        # Oldest audit record
        oldest_ts = session.scalar(
            select(func.min(AuditLog.timestamp))
        )
        oldest_age_days = (now - oldest_ts).days if oldest_ts else 0

        # Patient metrics
        total_patients = session.scalar(select(func.count(Patient.id))) or 0

        # Consent metrics (from consent table if exists, otherwise estimate)
        patients_with_consent = 0
        try:
            from cdss.db.models import Consent
            patients_with_consent = session.scalar(
                select(func.count(func.distinct(Consent.patient_id))).where(
                    Consent.revoked_at.is_(None)
                )
            ) or 0
        except Exception:
            # Consent model not yet migrated to DB
            patients_with_consent = 0

        # Retention status
        if oldest_age_days > DATA_RETENTION_DAYS:
            retention_status = "overdue"
        elif oldest_age_days > DATA_RETENTION_DAYS - 90:
            retention_status = "at_risk"
        else:
            retention_status = "compliant"

        consent_rate = round(100.0 * patients_with_consent / total_patients, 1) if total_patients > 0 else 0.0

        return {
            "total_audit_entries": total_audit,
            "audit_entries_today": audit_today,
            "total_patients": total_patients,
            "patients_with_consent": patients_with_consent,
            "consent_rate_percent": consent_rate,
            "data_retention_status": retention_status,
            "oldest_record_age_days": oldest_age_days,
            "retention_policy_days": DATA_RETENTION_DAYS,
            "compliance_score": _calculate_compliance_score(
                total_audit, audit_today, consent_rate, retention_status
            ),
            "checked_at": now.isoformat(),
        }


def _calculate_compliance_score(
    total_audit: int,
    audit_today: int,
    consent_rate: float,
    retention_status: str,
) -> float:
    """
    Calculate a 0-100 compliance score.
    Weighted: audit trail (30%), consent (40%), retention (30%).
    """
    # Audit: full marks if >0 entries today (system is logging)
    audit_score = 100.0 if audit_today > 0 else (50.0 if total_audit > 0 else 0.0)

    # Consent: percentage directly
    consent_score = consent_rate

    # Retention
    retention_score = {"compliant": 100.0, "at_risk": 50.0, "overdue": 0.0}.get(retention_status, 0.0)

    return round(0.30 * audit_score + 0.40 * consent_score + 0.30 * retention_score, 1)


def check_consent_status(patient_id: str) -> dict[str, Any]:
    """
    Check consent status for a specific patient.

    Returns consent records and overall status.
    """
    try:
        from cdss.db.models import Consent
        with get_session() as session:
            stmt = select(Consent).where(Consent.patient_id == patient_id)
            records = session.scalars(stmt).all()
            consents = [
                {
                    "id": r.id,
                    "consent_type": r.consent_type,
                    "purpose": r.purpose,
                    "granted_at": r.granted_at.isoformat() if r.granted_at else None,
                    "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
                    "is_active": r.revoked_at is None,
                }
                for r in records
            ]
            active_count = sum(1 for c in consents if c["is_active"])
            return {
                "patient_id": patient_id,
                "consents": consents,
                "active_consents": active_count,
                "has_active_consent": active_count > 0,
            }
    except Exception as e:
        logger.debug("Consent check failed (model may not be migrated): %s", e)
        return {
            "patient_id": patient_id,
            "consents": [],
            "active_consents": 0,
            "has_active_consent": False,
            "_note": "Consent table not yet available",
        }
