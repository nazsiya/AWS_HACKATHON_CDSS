"""
AgentCore Gateway tool Lambda – tools for all 5 CDSS agents + hospitals.

CDSS agents: Patient, Surgery, Resource, Scheduling, Engagement.
There is NO Triage agent.

Invoked by Bedrock AgentCore Gateway. Event = tool input props; tool name from
client_context.custom["bedrockAgentCoreToolName"] as TARGET___tool_name.
Response must match declared schema and include safety_disclaimer per CDSS.mdc.
See docs/agentcore-gateway-manual-steps.md.

When RDS_CONFIG_SECRET_NAME is set, queries live Aurora database;
otherwise returns synthetic/stub data.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "Hospital availability and suitability are indicative. "
    "Confirm capacity and eligibility with the facility before referral. "
    "This is not medical advice."
)

CLINICAL_DISCLAIMER = (
    "AI-generated clinical data is for decision support only. "
    "All decisions require qualified medical judgment. "
    "This system does not replace a doctor."
)


def _get_tool_name(event: Dict[str, Any], context: Any) -> str:
    """Strip TARGET___ prefix from bedrockAgentCoreToolName (context or event) to get tool name."""
    try:
        if context is not None and hasattr(context, "client_context") and context.client_context is not None:
            custom = getattr(context.client_context, "custom", None) or {}
            if hasattr(custom, "get"):
                tool_name = custom.get("bedrockAgentCoreToolName", "")
            else:
                tool_name = getattr(custom, "bedrockAgentCoreToolName", "") or ""
            if tool_name and "___" in str(tool_name):
                return str(tool_name).split("___", 1)[1]
            if tool_name:
                return str(tool_name)
    except Exception:
        pass
    return str(event.get("tool_name", event.get("__tool", "get_hospitals")))


# ─── Database helpers ───────────────────────────────────────────────

_db_engine = None


def _get_db_connection_step_log() -> str | None:
    """
    Run connection steps and return a short diagnostic string on first failure.
    Used for CloudWatch and optional tool response when DB is unavailable.
    """
    secret_name = os.environ.get("RDS_CONFIG_SECRET_NAME", "").strip()
    if not secret_name:
        return "RDS_CONFIG_SECRET_NAME not set"
    try:
        import boto3
        from urllib.parse import quote_plus
        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
        cfg = json.loads(raw)
        host = cfg.get("host", "")
        port = cfg.get("port", 5432)
        database = cfg.get("database", "cdssdb")
        username = cfg.get("username", "")
        if not host or not username:
            return "secret_missing_host_or_username"
    except Exception as e:
        logger.warning("[DB] secret_fetch failed: %s", e)
        return "secret_fetch_failed"

    try:
        rds_client = boto3.client("rds", region_name=region)
        password = rds_client.generate_db_auth_token(
            DBHostname=host, Port=port, DBUsername=username, Region=region,
        )
        db_url = f"postgresql+psycopg2://{username}:{quote_plus(password)}@{host}:{port}/{database}"
    except Exception as e:
        logger.warning("[DB] token_generate failed: %s", e)
        return "token_generate_failed"

    try:
        from sqlalchemy import create_engine
        engine = create_engine(db_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
    except Exception as e:
        logger.warning("[DB] engine_create failed: %s", e)
        return "engine_create_failed"

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("[DB] connect failed (host=%s): %s", host[:50] if host else "", e)
        return "connect_failed"
    return None


def _get_db_engine():
    """Lazily create a SQLAlchemy engine from Secrets Manager or DATABASE_URL."""
    global _db_engine
    if _db_engine is not None:
        return _db_engine

    db_url = os.environ.get("DATABASE_URL", "").strip()
    secret_name = os.environ.get("RDS_CONFIG_SECRET_NAME", "").strip()

    if not db_url and secret_name:
        try:
            import boto3
            from urllib.parse import quote_plus

            region = os.environ.get("AWS_REGION", "ap-south-1")
            sm = boto3.client("secretsmanager", region_name=region)
            raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
            cfg = json.loads(raw)
            host = cfg.get("host", "")
            port = cfg.get("port", 5432)
            database = cfg.get("database", "cdssdb")
            username = cfg.get("username", "")
            rds_client = boto3.client("rds", region_name=region)
            password = rds_client.generate_db_auth_token(
                DBHostname=host, Port=port, DBUsername=username, Region=region,
            )
            db_url = f"postgresql+psycopg2://{username}:{quote_plus(password)}@{host}:{port}/{database}?sslmode=require"
        except Exception as e:
            logger.warning("[DB] Cannot build DB URL from secret: %s", e)
            return None

    if not db_url:
        logger.info("[DB] No DATABASE_URL or RDS_CONFIG_SECRET_NAME; using synthetic data")
        return None

    try:
        from sqlalchemy import create_engine
        # connect_timeout so failures are fast and CloudWatch shows timeout vs other errors
        _db_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            connect_args={"connect_timeout": 5},
        )
        return _db_engine
    except Exception as e:
        logger.warning("[DB] Cannot create engine: %s", e)
        return None


def _query_hospitals_from_db(severity: str, limit: int) -> list | None:
    """Query hospitals table. Returns list of dicts or None if DB unavailable."""
    engine = _get_db_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, name, city, state, specialties, available_beds, "
                    "icu_beds, available_icu_beds, tier, emergency_available, contact_phone, "
                    "latitude, longitude "
                    "FROM hospitals WHERE status = 'active' "
                    "ORDER BY available_beds DESC LIMIT :lim"
                ),
                {"lim": limit},
            ).fetchall()
        hospitals = []
        for r in rows:
            hospitals.append({
                "id": r[0], "name": r[1], "city": r[2], "state": r[3],
                "specialties": r[4] if r[4] else [],
                "available_beds": r[5], "icu_beds": r[6],
                "available_icu_beds": r[7], "tier": r[8],
                "emergency_available": r[9], "contact_phone": r[10],
                "latitude": r[11], "longitude": r[12],
                "available": (r[5] or 0) > 0,
            })
        return hospitals
    except Exception as e:
        logger.warning("Hospital DB query failed: %s", e)
        return None


def _query_ot_status_from_db() -> list | None:
    """Query resources + schedule_slots for OT availability."""
    engine = _get_db_engine()
    if engine is None:
        return None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT r.id, r.name, r.status, r.availability, "
                    "  (SELECT COUNT(*) FROM schedule_slots ss "
                    "   WHERE ss.ot_id = r.id AND ss.status = 'available' "
                    "   AND ss.slot_date >= CURRENT_DATE) AS open_slots "
                    "FROM resources r WHERE r.type = 'ot' ORDER BY r.id"
                )
            ).fetchall()
        ots = []
        for r in rows:
            avail = r[3] if r[3] else {}
            ots.append({
                "ot_id": r[0], "name": r[1], "status": r[2],
                "area": avail.get("area", ""), "floor": avail.get("floor", ""),
                "next_free": avail.get("nextFree"),
                "open_slots_upcoming": r[4],
            })
        return ots
    except Exception as e:
        logger.warning("OT status DB query failed: %s", e)
        return None


# ─── Tool handlers (existing) ───────────────────────────────────────

def _get_hospitals(event: Dict[str, Any]) -> Dict[str, Any]:
    """Hospital list from DB or synthetic fallback."""
    severity = (event.get("severity") or "medium").lower()
    limit = min(int(event.get("limit", 5)), 20)
    hospitals = _query_hospitals_from_db(severity, limit)
    if hospitals is not None:
        return {"hospitals": hospitals, "source": "database", "safety_disclaimer": SAFETY_DISCLAIMER}
    hospitals = [
        {"id": f"H{i}", "name": f"Hospital {i} ({severity})", "distance_km": 2 + i, "available": True}
        for i in range(1, limit + 1)
    ]
    return {"hospitals": hospitals, "source": "synthetic", "safety_disclaimer": SAFETY_DISCLAIMER}


def _get_ot_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """OT status from DB or stub."""
    ots = _query_ot_status_from_db()
    if ots is not None:
        return {"operation_theaters": ots, "source": "database", "safety_disclaimer": SAFETY_DISCLAIMER}
    return {
        "available_slots": [],
        "message": "OT status unavailable; database not connected.",
        "source": "synthetic",
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def _get_abdm_record(event: Dict[str, Any]) -> Dict[str, Any]:
    """ABDM record lookup. When ABDM_SANDBOX_URL or MCP_ABDM_ENDPOINT is set (env or app config), calls API; else stub."""
    patient_id = (event.get("patient_id") or "").strip()
    if not patient_id:
        return {"error": "patient_id is required", "safety_disclaimer": SAFETY_DISCLAIMER}

    base_url = _get_abdm_endpoint()
    api_key = _get_abdm_api_key()
    if base_url:
        out = _http_get_abdm(base_url, patient_id, api_key)
        if out is not None:
            return {**out, "safety_disclaimer": CLINICAL_DISCLAIMER}

    return {
        "record_found": False,
        "message": "ABDM integration pending.",
        "patient_id": patient_id,
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def _get_abdm_endpoint() -> str:
    """ABDM or sandbox base URL from env or app config secret."""
    url = (os.environ.get("ABDM_SANDBOX_URL") or os.environ.get("MCP_ABDM_ENDPOINT") or "").strip().rstrip("/")
    if url:
        return url
    try:
        secret_name = os.environ.get("CDSS_APP_CONFIG_SECRET_NAME", "").strip()
        if not secret_name:
            return ""
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
        cfg = json.loads(raw)
        return (cfg.get("abdm_sandbox_url") or cfg.get("mcp_abdm_endpoint") or "").strip().rstrip("/")
    except Exception:
        return ""


def _get_abdm_api_key() -> str:
    """Optional API key for ABDM/sandbox from app config secret."""
    try:
        secret_name = os.environ.get("CDSS_APP_CONFIG_SECRET_NAME", "").strip()
        if not secret_name:
            return ""
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
        cfg = json.loads(raw)
        return (cfg.get("abdm_sandbox_api_key") or cfg.get("abdm_api_key") or "").strip()
    except Exception:
        return ""


def _http_get_abdm(base_url: str, patient_id: str, api_key: str) -> Dict[str, Any] | None:
    """GET ABDM/sandbox patient record; return dict or None on failure."""
    try:
        from urllib.request import Request, urlopen
        from urllib.parse import quote
        url = f"{base_url}/patient/record?patient_id={quote(patient_id)}"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("X-API-Key", api_key)
        with urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning("ABDM GET failed: %s", e)
        return None


# ─── Patient Agent tools ────────────────────────────────────────────

def _get_patient(event: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve a single patient by ID. Used by the Patient Agent via AgentCore."""
    patient_id = (event.get("patient_id") or "").strip()
    if not patient_id:
        return {"error": "patient_id is required", "safety_disclaimer": CLINICAL_DISCLAIMER}
    engine = _get_db_engine()
    if engine is None:
        return {"error": "Database not available", "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, name, date_of_birth, gender, language, abha_id, conditions, "
                     "allergies, vitals, blood_group, ward, severity, status, surgery_readiness "
                     "FROM patients WHERE id = :pid"),
                {"pid": patient_id},
            ).fetchone()
        if not row:
            return {"error": f"Patient {patient_id} not found", "safety_disclaimer": CLINICAL_DISCLAIMER}
        with engine.connect() as conn:
            visits = conn.execute(
                text("SELECT id, visit_date, doctor_id, department, diagnosis, notes "
                     "FROM visits WHERE patient_id = :pid ORDER BY visit_date DESC LIMIT 10"),
                {"pid": patient_id},
            ).fetchall()
        return {
            "patient": {
                "id": row[0], "name": row[1],
                "date_of_birth": str(row[2]) if row[2] else None,
                "gender": row[3], "language": row[4], "abha_id": row[5],
                "conditions": row[6] or [], "allergies": row[7] or [],
                "vitals": row[8] or {}, "blood_group": row[9],
                "ward": row[10], "severity": row[11], "status": row[12],
                "surgery_readiness": row[13] or {},
            },
            "visits": [
                {"id": v[0], "visit_date": str(v[1]) if v[1] else None,
                 "doctor_id": v[2], "department": v[3],
                 "diagnosis": v[4], "notes": v[5]}
                for v in visits
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_patient DB query failed: %s", e)
        return {"error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


def _list_patients(event: Dict[str, Any]) -> Dict[str, Any]:
    """List patients with optional filters. Used by the Patient Agent via AgentCore."""
    limit = min(int(event.get("limit", 20)), 50)
    status_filter = (event.get("status") or "").strip()
    engine = _get_db_engine()
    if engine is None:
        return {"patients": [], "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        query = "SELECT id, name, gender, ward, severity, status FROM patients"
        params: Dict[str, Any] = {"lim": limit}
        if status_filter:
            query += " WHERE status = :status"
            params["status"] = status_filter
        query += " ORDER BY created_at DESC LIMIT :lim"
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return {
            "patients": [
                {"id": r[0], "name": r[1], "gender": r[2], "ward": r[3],
                 "severity": r[4], "status": r[5]}
                for r in rows
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("list_patients DB query failed: %s", e)
        return {"patients": [], "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


# ─── Surgery Agent tools ────────────────────────────────────────────

def _get_surgeries(event: Dict[str, Any]) -> Dict[str, Any]:
    """List surgeries, optionally filtered by patient_id. Used by the Surgery Agent."""
    patient_id = (event.get("patient_id") or "").strip()
    limit = min(int(event.get("limit", 20)), 50)
    engine = _get_db_engine()
    if engine is None:
        return {"surgeries": [], "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        query = ("SELECT s.id, s.patient_id, s.surgery_type, s.classification, s.status, "
                 "s.scheduled_date, s.requirements, s.checklist, p.name AS patient_name "
                 "FROM surgeries s JOIN patients p ON s.patient_id = p.id")
        params: Dict[str, Any] = {"lim": limit}
        if patient_id:
            query += " WHERE s.patient_id = :pid"
            params["pid"] = patient_id
        query += " ORDER BY s.scheduled_date DESC LIMIT :lim"
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return {
            "surgeries": [
                {"id": r[0], "patient_id": r[1], "surgery_type": r[2],
                 "classification": r[3], "status": r[4],
                 "scheduled_date": str(r[5]) if r[5] else None,
                 "requirements": r[6] or {}, "checklist": r[7] or {},
                 "patient_name": r[8]}
                for r in rows
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_surgeries DB query failed: %s", e)
        return {"surgeries": [], "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


def _get_surgery(event: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve a single surgery by ID. Used by the Surgery Agent."""
    surgery_id = (event.get("surgery_id") or "").strip()
    if not surgery_id:
        return {"error": "surgery_id is required", "safety_disclaimer": CLINICAL_DISCLAIMER}
    engine = _get_db_engine()
    if engine is None:
        return {"error": "Database not available", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT s.id, s.patient_id, s.surgery_type, s.classification, s.status, "
                     "s.scheduled_date, s.requirements, s.checklist, s.duration_minutes, "
                     "s.complexity, p.name AS patient_name "
                     "FROM surgeries s JOIN patients p ON s.patient_id = p.id "
                     "WHERE s.id = :sid"),
                {"sid": surgery_id},
            ).fetchone()
        if not row:
            return {"error": f"Surgery {surgery_id} not found", "safety_disclaimer": CLINICAL_DISCLAIMER}
        return {
            "surgery": {
                "id": row[0], "patient_id": row[1], "surgery_type": row[2],
                "classification": row[3], "status": row[4],
                "scheduled_date": str(row[5]) if row[5] else None,
                "requirements": row[6] or {}, "checklist": row[7] or {},
                "duration_minutes": row[8], "complexity": row[9],
                "patient_name": row[10],
            },
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_surgery DB query failed: %s", e)
        return {"error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


# ─── Scheduling Agent tools ─────────────────────────────────────────

def _get_schedule(event: Dict[str, Any]) -> Dict[str, Any]:
    """Query schedule slots with optional date/ot filters. Used by the Scheduling Agent."""
    ot_id = (event.get("ot_id") or "").strip()
    date_filter = (event.get("date") or "").strip()
    limit = min(int(event.get("limit", 20)), 50)
    engine = _get_db_engine()
    if engine is None:
        return {"slots": [], "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        query = "SELECT id, ot_id, doctor_id, slot_date, start_time, end_time, status FROM schedule_slots"
        conditions = []
        params: Dict[str, Any] = {"lim": limit}
        if ot_id:
            conditions.append("ot_id = :ot_id")
            params["ot_id"] = ot_id
        if date_filter:
            conditions.append("slot_date = :slot_date")
            params["slot_date"] = date_filter
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY slot_date, start_time LIMIT :lim"
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return {
            "slots": [
                {"id": r[0], "ot_id": r[1], "doctor_id": r[2],
                 "slot_date": str(r[3]) if r[3] else None,
                 "start_time": str(r[4]) if r[4] else None,
                 "end_time": str(r[5]) if r[5] else None,
                 "status": r[6]}
                for r in rows
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_schedule DB query failed: %s", e)
        return {"slots": [], "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


def _find_replacement(event: Dict[str, Any]) -> Dict[str, Any]:
    """Find replacement staff by speciality. Used by the Scheduling Agent."""
    speciality = (event.get("speciality") or event.get("specialty") or "").strip()
    engine = _get_db_engine()
    if engine is None:
        return {"replacements": [], "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        query = "SELECT id, name, status, availability FROM resources WHERE type = 'staff'"
        params: Dict[str, Any] = {}
        if speciality:
            query += " AND (name ILIKE :spec OR availability::text ILIKE :spec)"
            params["spec"] = f"%{speciality}%"
        query += " AND status = 'available' ORDER BY name LIMIT 10"
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return {
            "replacements": [
                {"id": r[0], "name": r[1], "status": r[2], "availability": r[3] or {}}
                for r in rows
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("find_replacement DB query failed: %s", e)
        return {"replacements": [], "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


# ─── Engagement Agent tools ─────────────────────────────────────────

def _get_medications(event: Dict[str, Any]) -> Dict[str, Any]:
    """List medications for a patient. Used by the Engagement Agent."""
    patient_id = (event.get("patient_id") or "").strip()
    if not patient_id:
        return {"error": "patient_id is required", "safety_disclaimer": CLINICAL_DISCLAIMER}
    engine = _get_db_engine()
    if engine is None:
        return {"medications": [], "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, drug_name, dosage, frequency, start_date, end_date, active "
                     "FROM medications WHERE patient_id = :pid ORDER BY created_at DESC"),
                {"pid": patient_id},
            ).fetchall()
        return {
            "medications": [
                {"id": r[0], "drug_name": r[1], "dosage": r[2],
                 "frequency": r[3], "start_date": str(r[4]) if r[4] else None,
                 "end_date": str(r[5]) if r[5] else None, "active": r[6]}
                for r in rows
            ],
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_medications DB query failed: %s", e)
        return {"medications": [], "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


def _get_reminders_adherence(event: Dict[str, Any]) -> Dict[str, Any]:
    """Get reminder adherence stats for a patient. Used by the Engagement Agent."""
    patient_id = (event.get("patient_id") or "").strip()
    if not patient_id:
        return {"error": "patient_id is required", "safety_disclaimer": CLINICAL_DISCLAIMER}
    engine = _get_db_engine()
    if engine is None:
        return {"adherence": {}, "source": "synthetic", "safety_disclaimer": CLINICAL_DISCLAIMER}
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT "
                     "  COUNT(*) AS total, "
                     "  COUNT(*) FILTER (WHERE status = 'acknowledged') AS acked, "
                     "  COUNT(*) FILTER (WHERE status = 'pending') AS pending, "
                     "  COUNT(*) FILTER (WHERE status = 'overdue') AS overdue "
                     "FROM reminders WHERE patient_id = :pid"),
                {"pid": patient_id},
            ).fetchone()
        total = row[0] if row else 0
        acked = row[1] if row else 0
        return {
            "adherence": {
                "patient_id": patient_id,
                "total_reminders": total,
                "acknowledged": acked,
                "pending": row[2] if row else 0,
                "overdue": row[3] if row else 0,
                "adherence_rate": round(acked / total, 2) if total > 0 else 0.0,
            },
            "source": "database",
            "safety_disclaimer": CLINICAL_DISCLAIMER,
        }
    except Exception as e:
        logger.warning("get_reminders_adherence DB query failed: %s", e)
        return {"adherence": {}, "error": str(e), "safety_disclaimer": CLINICAL_DISCLAIMER}


# ─── Tool registry ──────────────────────────────────────────────────

TOOL_HANDLERS: Dict[str, Any] = {
    # Existing
    "get_hospitals": _get_hospitals,
    "get_ot_status": _get_ot_status,
    "get_abdm_record": _get_abdm_record,
    # Patient Agent
    "get_patient": _get_patient,
    "list_patients": _list_patients,
    # Surgery Agent
    "get_surgeries": _get_surgeries,
    "get_surgery": _get_surgery,
    # Scheduling Agent
    "get_schedule": _get_schedule,
    "find_replacement": _find_replacement,
    # Engagement Agent
    "get_medications": _get_medications,
    "get_reminders_adherence": _get_reminders_adherence,
}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Gateway invokes with tool input in event; dispatch by tool name from context.
    Returns JSON matching tool schema with safety_disclaimer for clinical tools.
    """
    tool_name = _get_tool_name(event, context)
    fn = TOOL_HANDLERS.get(tool_name)
    if fn is None:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(TOOL_HANDLERS.keys()),
            "safety_disclaimer": SAFETY_DISCLAIMER,
        }
    try:
        result = fn(event)
        return result
    except Exception as e:
        logger.exception("Gateway tool %s failed: %s", tool_name, e)
        return {
            "error": str(e),
            "tool": tool_name,
            "safety_disclaimer": SAFETY_DISCLAIMER,
        }
