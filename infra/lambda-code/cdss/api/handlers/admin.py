"""
Admin API handler – users, audit log, config, analytics.

GET /api/v1/admin/audit: from audit_log table (Aurora).
GET /api/v1/admin/users: from Cognito User Pool when cognito_user_pool_id is set (Secrets Manager or env); otherwise stub.
GET/PUT /api/v1/admin/config: from SSM /cdss/admin/config when available; fallback in-memory stub for local dev.
GET /api/v1/admin/analytics: from Aurora (OT utilization, reminder stats).
Per project-conventions: RBAC enforced by router; no PHI in logs.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select

from cdss.api.handlers.common import cors_headers, json_response, parse_body_json, query_int
from cdss.db.models import AuditLog, Reminder, Surgery
from cdss.db.session import get_session

logger = logging.getLogger(__name__)

# Fallback in-memory config when SSM is not available (e.g. local dev without /cdss/admin/config).
# When cognito_user_pool_id or SSM is unset, endpoints document that they run in stub mode.
_ADMIN_CONFIG_FALLBACK: dict = {
    "mcpHospitalEndpoint": "",
    "mcpAbdmEndpoint": "",
    "featureFlags": {"aiAssist": True, "voiceInput": False},
}

SSM_ADMIN_CONFIG_NAME = "/cdss/admin/config"
COGNITO_USER_POOL_ID_ENV = "COGNITO_USER_POOL_ID"


def _get_cognito_pool_id() -> str:
    """Cognito User Pool ID from AWS Secrets Manager (CDSS_APP_CONFIG_SECRET_NAME) or env."""
    try:
        from cdss.config.secrets import get_app_config
        cfg = get_app_config()
        pool_id = (cfg.get("cognito_user_pool_id") or "").strip()
        if pool_id:
            return pool_id
    except Exception:
        pass
    return (os.environ.get(COGNITO_USER_POOL_ID_ENV) or "").strip()


def _list_audit(limit: int) -> dict:
    """Return audit log items from Aurora."""
    with get_session() as session:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(min(limit, 500))
        )
        rows = session.scalars(stmt).all()
        items = [
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_email": r.user_email,
                "action": r.action,
                "resource": r.resource,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ]
        return json_response(200, {"items": items})


def _list_users() -> dict:
    """
    Return users from Cognito User Pool when cognito_user_pool_id is set (Secrets Manager or env).
    Otherwise returns empty list (stub mode for local dev without Cognito).
    """
    pool_id = _get_cognito_pool_id()
    if not pool_id or not pool_id.strip():
        logger.debug("Admin users: stub mode (cognito_user_pool_id not set)")
        return json_response(200, {"users": [], "_stub": "Set CDSS_APP_CONFIG_SECRET_NAME (with cognito_user_pool_id) or COGNITO_USER_POOL_ID to list Cognito users"})

    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("cognito-idp")
        paginator = client.get_paginator("list_users")
        users: list[dict] = []
        for page in paginator.paginate(UserPoolId=pool_id):
            for u in page.get("Users") or []:
                attrs = {a["Name"]: a["Value"] for a in (u.get("Attributes") or [])}
                email = attrs.get("email") or attrs.get("preferred_username")
                name = attrs.get("name") or attrs.get("preferred_username") or email or u.get("Username")
                role = attrs.get("custom:role") or attrs.get("role") or "user"
                users.append({
                    "id": u.get("Username"),
                    "username": u.get("Username"),
                    "name": name,
                    "email": email,
                    "role": role,
                    "status": "active" if u.get("Enabled", True) else "inactive",
                    "enabled": u.get("Enabled", True),
                    "user_create_date": u.get("UserCreateDate").isoformat() if u.get("UserCreateDate") else None,
                })
        return json_response(200, {"users": users})
    except ClientError as e:
        logger.warning(
            "Cognito list_users failed; returning empty list",
            extra={"error_code": e.response.get("Error", {}).get("Code")},
        )
        return json_response(200, {"users": [], "error": "Cognito unavailable"})
    except Exception as e:
        logger.warning("Admin users error", extra={"error": str(e)}, exc_info=True)
        return json_response(200, {"users": []})


def _get_config() -> dict:
    """
    Return system config from SSM /cdss/admin/config.
    Fallback to in-memory stub when SSM is unavailable (e.g. local dev).
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("ssm")
        resp = client.get_parameter(Name=SSM_ADMIN_CONFIG_NAME)
        raw = resp.get("Parameter", {}).get("Value")
        if raw:
            data = json.loads(raw)
            return json_response(200, data)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ParameterNotFound":
            logger.warning("SSM get_parameter failed", extra={"error": str(e)})
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("SSM admin config invalid JSON", extra={"error": str(e)})
    return json_response(200, {**_ADMIN_CONFIG_FALLBACK.copy(), "_stub": "Using fallback; set SSM /cdss/admin/config for persisted config"})


def _update_config(body: dict) -> dict:
    """
    Update system config in SSM /cdss/admin/config.
    Merges with existing; falls back to in-memory update when SSM write fails (e.g. local dev).
    """
    if not body:
        return _get_config()
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("ssm")
        try:
            resp = client.get_parameter(Name=SSM_ADMIN_CONFIG_NAME)
            current = json.loads(resp.get("Parameter", {}).get("Value") or "{}")
        except ClientError:
            current = _ADMIN_CONFIG_FALLBACK.copy()
        current.update(body)
        client.put_parameter(
            Name=SSM_ADMIN_CONFIG_NAME,
            Value=json.dumps(current),
            Type="String",
            Overwrite=True,
        )
        return json_response(200, current)
    except ClientError as e:
        logger.warning("SSM put_parameter failed", extra={"error": str(e)})
    except Exception as e:
        logger.warning("Admin config update failed", extra={"error": str(e)})
    # Fallback: in-memory (not persisted)
    _ADMIN_CONFIG_FALLBACK.update(body)
    return json_response(200, {**_ADMIN_CONFIG_FALLBACK.copy(), "_stub": "Config updated in memory only; SSM write failed"})


def _get_analytics() -> dict:
    """Aggregate analytics from Aurora: OT utilization (schedule_slots), reminder stats, conflicts."""
    try:
        from cdss.db.models import ScheduleSlot
        from sqlalchemy import case

        with get_session() as session:
            # OT utilization from schedule_slots (Phase 6): per (ot_id, slot_date) then aggregate by ot_id
            stmt = (
                select(
                    ScheduleSlot.ot_id,
                    ScheduleSlot.slot_date,
                    func.count(ScheduleSlot.id).label("total"),
                    func.sum(case((ScheduleSlot.status == "booked", 1), else_=0)).label("booked"),
                )
                .where(ScheduleSlot.ot_id.isnot(None), ScheduleSlot.slot_date.isnot(None))
                .group_by(ScheduleSlot.ot_id, ScheduleSlot.slot_date)
            )
            rows = session.execute(stmt).all()
            by_ot: dict[str, list[float]] = {}
            for r in rows:
                total = r.total or 0
                booked = r.booked or 0
                pct = round(100.0 * booked / total, 1) if total else 0
                by_ot.setdefault(r.ot_id, []).append(pct)
            ot_utilization = [
                {"ot": ot_id, "percent": round(sum(pcts) / len(pcts), 0) if pcts else 0}
                for ot_id, pcts in by_ot.items()
            ]
            if not ot_utilization:
                ot_utilization = [{"ot": "—", "percent": 0}]

            # OT conflicts: same ot_id, slot_date, slot_time with multiple slots
            slot_stmt = (
                select(ScheduleSlot)
                .where(ScheduleSlot.ot_id.isnot(None), ScheduleSlot.slot_date.isnot(None))
                .order_by(ScheduleSlot.ot_id, ScheduleSlot.slot_date, ScheduleSlot.slot_time)
            )
            slots = list(session.scalars(slot_stmt).all())
            groups = defaultdict(list)
            for s in slots:
                k = (s.ot_id or "", str(s.slot_date) if s.slot_date else "", s.slot_time or "")
                if k[0] and k[1]:
                    groups[k].append(s)
            ot_conflicts = [
                {
                    "id": f"{k[0]}-{k[1]}-{k[2]}",
                    "ot": k[0],
                    "date": k[1],
                    "time": k[2],
                    "message": f"OT {k[0]} double-booked on {k[1]} at {k[2]}",
                }
                for k, group in groups.items()
                if len(group) >= 2
            ]

            # Reminder stats
            total_reminders = session.scalar(select(func.count(Reminder.id))) or 0
            sent_reminders = (
                session.scalar(
                    select(func.count(Reminder.id)).where(Reminder.sent_at.isnot(None))
                )
                or 0
            )
            reminder_stats = {
                "sent": sent_reminders,
                "acknowledged": sent_reminders,
                "overdue": max(0, total_reminders - sent_reminders),
            }

            return json_response(
                200,
                {
                    "otUtilization": ot_utilization,
                    "otRecommendations": "",
                    "otConflicts": ot_conflicts,
                    "agentUsage": [],
                    "reminderStats": reminder_stats,
                },
            )
    except Exception as e:
        logger.warning(
            "Analytics aggregation failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        return json_response(
            200,
            {
                "otUtilization": [],
                "otRecommendations": "",
                "otConflicts": [],
                "agentUsage": [],
                "reminderStats": {"sent": 0, "acknowledged": 0, "overdue": 0},
            },
        )


def _get_compliance() -> dict:
    """GET /api/v1/admin/compliance – DISHA compliance dashboard."""
    try:
        from cdss.services.compliance import get_compliance_dashboard
        data = get_compliance_dashboard()
        return json_response(200, data)
    except Exception as e:
        logger.warning("Compliance dashboard error", extra={"error": str(e)})
        return json_response(200, {
            "total_audit_entries": 0,
            "audit_entries_today": 0,
            "total_patients": 0,
            "patients_with_consent": 0,
            "consent_rate_percent": 0.0,
            "data_retention_status": "unknown",
            "oldest_record_age_days": 0,
            "retention_policy_days": 2555,
            "compliance_score": 0.0,
            "_error": str(e),
        })


def _export_audit(event: dict) -> dict:
    """GET /api/v1/admin/audit/export – download audit log as CSV."""
    try:
        from cdss.services.compliance import generate_audit_report

        params = event.get("queryStringParameters") or {}
        date_from_str = params.get("from")
        date_to_str = params.get("to")

        date_from = None
        date_to = None
        if date_from_str:
            from datetime import datetime as dt
            date_from = dt.strptime(date_from_str[:10], "%Y-%m-%d").date()
        if date_to_str:
            from datetime import datetime as dt
            date_to = dt.strptime(date_to_str[:10], "%Y-%m-%d").date()

        csv_data = generate_audit_report(date_from=date_from, date_to=date_to)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/csv",
                "Content-Disposition": "attachment; filename=cdss_audit_report.csv",
                **cors_headers(event),
            },
            "body": csv_data,
        }
    except Exception as e:
        logger.warning("Audit export error", extra={"error": str(e)})
        return json_response(500, {"error": "Audit export failed", "detail": str(e)})


def handler(event: dict, context: object) -> dict:
    """Handle GET/PUT /api/v1/admin/*. RBAC enforced by router (admin only)."""
    try:
        method = (event.get("httpMethod") or "GET").upper()
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""
        parts = [p for p in proxy.split("/") if p]

        if len(parts) < 2 or parts[0].lower() != "v1" or parts[1].lower() != "admin":
            return json_response(404, {"error": "Not found"})

        sub = parts[2].lower() if len(parts) > 2 else ""
        if not sub:
            return json_response(
                200,
                {"admin": True, "endpoints": ["audit", "users", "config", "analytics"]},
            )

        if sub == "audit":
            if len(parts) > 3 and parts[3].lower() == "export":
                return _export_audit(event)
            limit = query_int(event, "limit", 100)
            return _list_audit(limit)
        if sub == "users":
            return _list_users()
        if sub == "config":
            if method == "GET":
                return _get_config()
            if method == "PUT":
                return _update_config(parse_body_json(event))
            return json_response(405, {"error": "Method not allowed"})
        if sub == "analytics":
            return _get_analytics()
        if sub == "resources":
            return json_response(200, {"resources": []})
        if sub == "compliance":
            return _get_compliance()


        return json_response(404, {"error": "Not found"})
    except Exception as e:
        logger.error(
            "Admin handler error",
            extra={"error": str(e), "handler": "admin"},
            exc_info=True,
        )
        return json_response(500, {"error": "Internal server error"})
