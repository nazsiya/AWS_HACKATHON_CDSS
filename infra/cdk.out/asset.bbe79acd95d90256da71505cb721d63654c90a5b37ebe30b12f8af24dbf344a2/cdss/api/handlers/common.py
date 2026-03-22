"""
Common helpers for CDSS Lambda handlers.

These helpers are intentionally small and framework-free so they work in AWS Lambda
and in local tests with API Gateway proxy events.
"""

from __future__ import annotations

import json
import os
from typing import Any


_DEFAULT_CORS_ALLOW_METHODS = "GET,POST,PUT,DELETE,OPTIONS"
_DEFAULT_CORS_ALLOW_HEADERS = "Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
_DEFAULT_CORS_MAX_AGE = "86400"


def _get_header(event: dict | None, name: str) -> str | None:
    if not event:
        return None
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        return None
    # API Gateway header keys are not guaranteed to be normalized.
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.upper())


def cors_headers(event: dict | None = None) -> dict[str, str]:
    """
    Build CORS headers for API Gateway proxy responses.

    Configuration (via env vars):
    - CORS_ALLOW_ORIGINS: comma-separated list of allowed origins, or "*" (default: "*")
    - CORS_ALLOW_HEADERS: allowed request headers (default includes Authorization + Content-Type)
    - CORS_ALLOW_METHODS: allowed methods (default: GET,POST,PUT,DELETE,OPTIONS)
    - CORS_MAX_AGE: preflight cache max-age seconds (default: 86400)

    Notes:
    - When CORS_ALLOW_ORIGINS is a list, this function reflects the incoming Origin only when allowed.
    - When reflecting Origin, it sets Vary: Origin to avoid cache poisoning.
    """
    allow_origins_raw = (os.environ.get("CORS_ALLOW_ORIGINS") or "*").strip()
    allow_headers = (os.environ.get("CORS_ALLOW_HEADERS") or _DEFAULT_CORS_ALLOW_HEADERS).strip() or _DEFAULT_CORS_ALLOW_HEADERS
    allow_methods = (os.environ.get("CORS_ALLOW_METHODS") or _DEFAULT_CORS_ALLOW_METHODS).strip() or _DEFAULT_CORS_ALLOW_METHODS
    max_age = (os.environ.get("CORS_MAX_AGE") or _DEFAULT_CORS_MAX_AGE).strip() or _DEFAULT_CORS_MAX_AGE

    origin = _get_header(event, "Origin")
    allow_origin: str | None = None

    if allow_origins_raw == "*":
        allow_origin = "*"
    else:
        allowed = [o.strip() for o in allow_origins_raw.split(",") if o.strip()]
        if "*" in allowed:
            allow_origin = "*"
        elif origin and origin in allowed:
            allow_origin = origin

    out: dict[str, str] = {
        "Access-Control-Allow-Headers": allow_headers,
        "Access-Control-Allow-Methods": allow_methods,
        "Access-Control-Max-Age": max_age,
    }
    if allow_origin:
        out["Access-Control-Allow-Origin"] = allow_origin
        if allow_origin != "*":
            out["Vary"] = "Origin"
    return out


def json_response(
    status_code: int,
    body: Any,
    event: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    base_headers = {
        "Content-Type": "application/json",
        **cors_headers(event),
    }
    if headers:
        base_headers.update(headers)
    return {
        "statusCode": int(status_code),
        "headers": base_headers,
        "body": json.dumps(body, default=str),
    }


def parse_body_json(event: dict) -> dict:
    raw = event.get("body")
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def query_int(event: dict, name: str, default: int) -> int:
    params = event.get("queryStringParameters") or {}
    try:
        v = params.get(name)
        if v is None:
            return int(default)
        return int(str(v).strip())
    except (ValueError, TypeError):
        return default

# Re-export from i18n for convenience – handlers can import from either location.
from cdss.services.i18n import get_request_language  # noqa: E402, F401
