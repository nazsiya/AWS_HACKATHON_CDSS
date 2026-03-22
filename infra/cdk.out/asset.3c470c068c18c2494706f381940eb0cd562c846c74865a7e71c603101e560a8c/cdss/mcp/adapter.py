"""
MCP adapter layer – single entry point for external systems.

CDSS agents: Patient, Surgery, Resource, Scheduling, Engagement.
Design allows adding Clinical Protocols and Telemedicine MCPs later without
changing agent interfaces.

When MCP_HOSPITAL_ENDPOINT or MCP_ABDM_ENDPOINT / ABDM_SANDBOX_URL are set
(via env or app config from Secrets Manager), the adapter calls real/sandbox
APIs. Otherwise returns stub data (Phase 2.2, 2.3, 2.4).

All calls are logged via event_log for Req 8 audit (inter-agent communication).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Timeout for external MCP HTTP calls (seconds)
_MCP_HTTP_TIMEOUT = 10


def _get_mcp_config() -> Dict[str, Any]:
    """MCP endpoints and optional auth from app config (Secrets Manager) or env."""
    try:
        from cdss.config.secrets import get_app_config
        cfg = get_app_config()
    except Exception:
        cfg = {}
    base = cfg.copy()
    base.setdefault("mcp_hospital_endpoint", (os.environ.get("MCP_HOSPITAL_ENDPOINT") or "").strip())
    base.setdefault("mcp_abdm_endpoint", (os.environ.get("MCP_ABDM_ENDPOINT") or "").strip())
    base.setdefault("abdm_sandbox_url", (os.environ.get("ABDM_SANDBOX_URL") or "").strip())
    return base


def _http_get(url: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """GET url; return parsed JSON or None on failure."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("X-API-Key", api_key)
        with urllib.request.urlopen(req, timeout=_MCP_HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except Exception as e:
        logger.debug("MCP HTTP GET %s failed: %s", url[:50], e)
        return None


def get_hospital_data(data_type: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch hospital data (OT status, beds, etc.) from Hospital Systems MCP.
    data_type: "ot_status" | "beds" | "equipment"

    When MCP_HOSPITAL_ENDPOINT (or app_config.mcp_hospital_endpoint) is set,
    calls the external API; otherwise returns stub (Phase 2.4).
    """
    start = time.perf_counter()
    config = _get_mcp_config()
    base_url = (config.get("mcp_hospital_endpoint") or "").strip().rstrip("/")
    api_key = (config.get("hospital_mcp_api_key") or config.get("mcp_hospital_api_key") or "").strip()

    if base_url:
        path = {"ot_status": "/mcp/ot_status", "beds": "/mcp/beds", "equipment": "/mcp/equipment"}.get(
            data_type, f"/mcp/{data_type}"
        )
        url = base_url + path
        result = _http_get(url, api_key or None)
        if result is not None:
            duration_ms = int((time.perf_counter() - start) * 1000)
            _log_mcp_event(
                action=f"get_hospital_data:{data_type}",
                success=True,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
            return result

    # Stub responses until external API is integrated or on failure
    if data_type == "ot_status":
        result = {"ots": [{"id": "OT-1", "status": "available", "name": "OT 1"}]}
    elif data_type == "beds":
        result = {"beds": [{"id": "B-1", "status": "available", "ward": "General"}]}
    elif data_type == "equipment":
        result = {"equipment": []}
    else:
        result = {"error": f"Unknown type: {data_type}"}

    duration_ms = int((time.perf_counter() - start) * 1000)
    _log_mcp_event(
        action=f"get_hospital_data:{data_type}",
        success="error" not in result,
        duration_ms=duration_ms,
        correlation_id=correlation_id,
    )
    return result


def get_abdm_record(patient_id: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch patient record from ABDM EHR (or sandbox). When MCP_ABDM_ENDPOINT or
    ABDM_SANDBOX_URL is set, calls the external API; otherwise returns stub (Phase 2.3).
    """
    start = time.perf_counter()

    if not patient_id:
        result: Dict[str, Any] = {"error": "patient_id required"}
        duration_ms = int((time.perf_counter() - start) * 1000)
        _log_mcp_event(action="get_abdm_record", success=False, duration_ms=duration_ms, correlation_id=correlation_id)
        return result

    config = _get_mcp_config()
    base_url = (config.get("mcp_abdm_endpoint") or config.get("abdm_sandbox_url") or "").strip().rstrip("/")
    api_key = (config.get("abdm_sandbox_api_key") or config.get("abdm_api_key") or "").strip()

    if base_url:
        # Common sandbox pattern: GET /patient/record?patient_id=PT-1001 or /gateway/v1/patient/record?abha_id=...
        url = f"{base_url}/patient/record?patient_id={urllib.request.quote(patient_id)}"
        if "/gateway/" in base_url:
            url = f"{base_url}/record?patient_id={urllib.request.quote(patient_id)}"
        out = _http_get(url, api_key or None)
        if out is not None and "error" not in out:
            duration_ms = int((time.perf_counter() - start) * 1000)
            _log_mcp_event(action="get_abdm_record", success=True, duration_ms=duration_ms, correlation_id=correlation_id)
            return {**out, "patient_id": patient_id}

    result = {
        "patient_id": patient_id,
        "abdm_linked": False,
        "summary": "ABDM integration pending",
    }
    duration_ms = int((time.perf_counter() - start) * 1000)
    _log_mcp_event(action="get_abdm_record", success=True, duration_ms=duration_ms, correlation_id=correlation_id)
    return result


def _log_mcp_event(
    action: str,
    success: bool,
    duration_ms: int,
    correlation_id: Optional[str] = None,
) -> None:
    """Log MCP adapter call as inter-agent event."""
    try:
        from cdss.services.event_log import log_agent_event

        log_agent_event(
            source_agent="mcp_adapter",
            target_agent="hospital_mcp",
            action=action,
            correlation_id=correlation_id,
            success=success,
            duration_ms=duration_ms,
        )
    except Exception:
        pass
