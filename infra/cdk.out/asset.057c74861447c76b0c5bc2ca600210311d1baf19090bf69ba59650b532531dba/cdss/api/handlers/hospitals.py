"""
Hospitals endpoint (Phase 1–2).

This is a pragmatic API endpoint for looking up referral facilities / hospitals.
It can query Aurora (if `hospitals` table exists) or fall back to synthetic results.
"""

from __future__ import annotations

import logging

from cdss.api.handlers.common import json_response, parse_body_json, query_int

logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "Hospital availability and suitability are indicative. Confirm capacity and eligibility with the facility. "
    "This is not medical advice."
)


def _synthetic_hospitals(severity: str, limit: int) -> list[dict]:
    return [
        {"id": f"H{i}", "name": f"Hospital {i} ({severity})", "distance_km": 2 + i, "available": True}
        for i in range(1, limit + 1)
    ]


def _query_hospitals(severity: str, limit: int) -> list[dict] | None:
    try:
        from sqlalchemy import text

        from cdss.db.session import get_session

        with get_session() as session:
            rows = session.execute(
                text(
                    "SELECT id, name, city, state, specialties, available_beds, icu_beds, available_icu_beds, "
                    "tier, emergency_available, contact_phone, latitude, longitude "
                    "FROM hospitals WHERE status = 'active' "
                    "ORDER BY available_beds DESC NULLS LAST LIMIT :lim"
                ),
                {"lim": limit},
            ).fetchall()
        hospitals: list[dict] = []
        for r in rows:
            hospitals.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "city": r[2],
                    "state": r[3],
                    "specialties": r[4] if r[4] else [],
                    "available_beds": r[5],
                    "icu_beds": r[6],
                    "available_icu_beds": r[7],
                    "tier": r[8],
                    "emergency_available": r[9],
                    "contact_phone": r[10],
                    "latitude": r[11],
                    "longitude": r[12],
                    "available": (r[5] or 0) > 0,
                }
            )
        return hospitals
    except Exception as exc:
        logger.debug("Hospitals DB query unavailable", extra={"error": str(exc)})
        return None


def hospitals_handler(event: dict, context: object) -> dict:
    """
    - GET  /api/v1/hospitals?limit=5&severity=medium
    - POST /api/v1/hospitals  body: { severity, limit }
    """
    method = (event.get("httpMethod") or "GET").upper()
    severity = "medium"
    limit = 5

    if method == "POST":
        body = parse_body_json(event)
        severity = (body.get("severity") or severity).strip().lower()
        try:
            limit = int(body.get("limit", limit))
        except Exception:
            limit = 5
    else:
        params = event.get("queryStringParameters") or {}
        severity = (params.get("severity") or severity).strip().lower()
        limit = query_int(event, "limit", limit)

    limit = min(max(int(limit), 1), 20)
    severity = severity if severity in {"low", "medium", "high", "critical"} else "medium"

    hospitals = _query_hospitals(severity, limit)
    if hospitals is None:
        hospitals = _synthetic_hospitals(severity, limit)
        source = "synthetic"
    else:
        source = "database"

    return json_response(
        200,
        {
            "severity": severity,
            "hospitals": hospitals,
            "source": source,
            "safety_disclaimer": SAFETY_DISCLAIMER,
        },
    )

"""
Hospital Matcher – AgentCore or Converse/stub fallback with tracing.

POST/GET /api/v1/hospitals: when USE_AGENTCORE=true and AGENT_RUNTIME_ARN set,
invokes AgentCore Runtime; otherwise returns stub/synthetic list. Logs
HospitalMatcher source=agentcore|converse|bedrock_agent duration_ms= for audit (CDSS.mdc).
See docs/agentcore-implementation-plan.md and docs/agentcore-next-steps-implementation.md.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "Hospital availability and suitability are indicative. "
    "Confirm capacity and eligibility with the facility before referral. "
    "This is not medical advice."
)


def _fallback_hospitals(severity: str, limit: int) -> Dict[str, Any]:
    """Stub response when AgentCore is disabled or unavailable. CDSS.mdc: safety_disclaimer."""
    limit = min(max(1, limit), 20)
    hospitals = [
        {
            "id": f"H{i}",
            "name": f"Hospital {i} ({severity})",
            "distance_km": 2 + i,
            "available": True,
        }
        for i in range(1, limit + 1)
    ]
    return {"hospitals": hospitals, "safety_disclaimer": SAFETY_DISCLAIMER}


def _invoke_agentcore_runtime(body: Dict[str, Any], runtime_arn: str) -> Dict[str, Any]:
    """
    Call Bedrock AgentCore InvokeAgentRuntime. Returns parsed response or raises.
    """
    try:
        import uuid
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        client = boto3.client("bedrock-agentcore", region_name=region)
        payload = json.dumps(body).encode("utf-8")
        session_id = str(uuid.uuid4())
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            contentType="application/json"
        )
        result = resp.get("response")
        if result is None:
            return {"hospitals": [], "safety_disclaimer": SAFETY_DISCLAIMER}
        if hasattr(result, "read"):
            data = json.loads(result.read().decode("utf-8"))
        else:
            data = result if isinstance(result, dict) else {}
        return data if isinstance(data, dict) else {"hospitals": [], "safety_disclaimer": SAFETY_DISCLAIMER}
    except Exception as e:
        logger.warning("AgentCore InvokeAgentRuntime failed: %s", e)
        raise


def hospitals_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST/GET /api/v1/hospitals. USE_AGENTCORE + AGENT_RUNTIME_ARN → AgentCore;
    else fallback. Logs HospitalMatcher source=... duration_ms=... (no PHI).
    """
    start = time.perf_counter()
    body = {}
    try:
        raw = event.get("body")
        if raw:
            body = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass
    severity = (body.get("severity") or "medium").lower()
    limit = min(int(body.get("limit", 5)), 20)

    use_agentcore = os.environ.get("USE_AGENTCORE", "").strip().lower() == "true"
    runtime_arn = (os.environ.get("AGENT_RUNTIME_ARN") or "").strip()

    source = "bedrock_agent"
    try:
        if use_agentcore and runtime_arn:
            try:
                out = _invoke_agentcore_runtime(
                    {"severity": severity, "limit": limit},
                    runtime_arn,
                )
                source = "agentcore"
                if "hospitals" not in out:
                    out = _fallback_hospitals(severity, limit)
            except Exception:
                out = _fallback_hospitals(severity, limit)
                source = "converse"
        else:
            out = _fallback_hospitals(severity, limit)
            source = "converse"
    except Exception as e:
        logger.exception("HospitalMatcher error: %s", e)
        out = _fallback_hospitals(severity, limit)
        source = "converse"

    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "HospitalMatcher source=%s duration_ms=%d",
        source,
        duration_ms,
        extra={"source": source, "duration_ms": duration_ms},
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(out),
    }
