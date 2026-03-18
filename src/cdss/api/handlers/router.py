"""CDSS API router - proxy for API Gateway with Cognito RBAC and audit logging."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from cdss.api.handlers.common import cors_headers, json_response
from cdss.api.handlers.dashboard import get_dashboard_data

logger = logging.getLogger(__name__)

# Path prefixes that require admin role (admin or superuser)
ADMIN_PATHS = ("/api/v1/admin", "/admin")

# Role that bypasses all RBAC restrictions (admin paths + patient scoping)
SUPERUSER_ROLE = "superuser"


def _repo_root() -> Path:
    """Best-effort repo root (for docs/swagger.yaml). Prefer env, then relative to this file."""
    root = os.environ.get("CDSS_REPO_ROOT")
    if root:
        return Path(root)
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "docs" / "swagger.yaml").exists():
            return p
        p = p.parent
    return Path(os.getcwd())


def _serve_swagger_yaml(event: Dict[str, Any]) -> Dict[str, Any]:
    """GET /docs/swagger.yaml – serve OpenAPI spec."""
    try:
        path = _repo_root() / "docs" / "swagger.yaml"
        body = path.read_text(encoding="utf-8")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/yaml",
                **cors_headers(event),
            },
            "body": body,
        }
    except Exception as e:
        logger.warning("Swagger YAML serve failed: %s", e)
        return json_response(404, {"error": "swagger.yaml not found"}, event=event)


def _serve_swagger_ui(event: Dict[str, Any]) -> Dict[str, Any]:
    """GET /api/docs – Swagger UI HTML."""
    base = event.get("requestContext", {}).get("path", "").replace("/api/docs", "") or ""
    spec_url = (base.rstrip("/") + "/docs/swagger.yaml") or "/docs/swagger.yaml"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>CDSS API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{
      url: "{spec_url}",
      dom_id: "#swagger-ui",
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset]
    }});
  </script>
</body>
</html>"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html; charset=utf-8",
            **cors_headers(event),
        },
        "body": html,
    }


def _get_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract JWT claims from API Gateway request context (Cognito authorizer)."""
    try:
        ctx = event.get("requestContext") or {}
        authorizer = ctx.get("authorizer") or {}
        # Cognito passes claims under authorizer.claims
        claims = authorizer.get("claims") or authorizer or {}
        return claims if isinstance(claims, dict) else {}
    except Exception as exc:  # best-effort; fall back to anonymous
        logger.warning("Failed to extract claims", extra={"error": str(exc)})
        return {}


def _get_role(claims: Dict[str, Any]) -> str:
    """Resolve role from Cognito custom attribute or claim."""
    return (
        (claims.get("custom:role") or claims.get("role") or "")
        .strip()
        .strip("'\"")
        .lower()
    )


def _get_user_id(claims: Dict[str, Any]) -> str:
    return (claims.get("sub") or claims.get("username") or "").strip()


def _get_email(claims: Dict[str, Any]) -> str:
    return (claims.get("email") or claims.get("cognito:username") or "").strip()


def _get_patient_id(claims: Dict[str, Any]) -> str:
    """
    Resolve patientId for patient-scoped RBAC.

    Prefer explicit Cognito attributes (custom:patientId / patientId); fall back to sub.
    """
    return (
        claims.get("custom:patientId")
        or claims.get("patientId")
        or claims.get("sub")
        or ""
    ).strip()


def _path_requires_admin(path: str) -> bool:
    """True if path is an admin-only path (handles /stage/api/v1/admin or /api/v1/admin)."""
    path_normalized = (path or "").strip().lower()
    # Strip leading stage segment if present (e.g. /dev/api/... -> /api/...)
    if path_normalized.startswith("/dev/") or path_normalized.startswith("/prod/"):
        path_normalized = "/" + path_normalized.split("/", 2)[-1]
    return any(path_normalized.startswith(p.strip().lower()) for p in ADMIN_PATHS)


def _is_superuser(role: str) -> bool:
    """True if role has full access (all admin paths and no patient-scope restrictions)."""
    return (role or "").strip().lower() == SUPERUSER_ROLE


def _can_access_admin_paths(role: str) -> bool:
    """True if role is allowed to access admin-only paths."""
    r = (role or "").strip().lower()
    return r == "admin" or r == SUPERUSER_ROLE


def _audit_log(event: dict, action: str, resource: str, resource_id: str | None = None, details: dict | None = None) -> None:
    """Best-effort async-ish audit log write to RDS."""
    try:
        from cdss.db.models import AuditLog
        from cdss.db.session import get_session
        import os

        # Skip audit log if database is not configured (mock mode)
        if not os.environ.get("DATABASE_URL"):
            logger.debug("Skipping audit log: DATABASE_URL not set (Mock Mode)")
            return

        user_id = "ANONYMOUS"
        user_email = None
        auth = event.get("requestContext", {}).get("authorizer")
        if auth:
            # Cognito authorizer
            claims = auth.get("claims") or {}
            user_id = claims.get("sub") or claims.get("username") or "ANONYMOUS"
            user_email = claims.get("email")

        with get_session() as session:
            log_entry = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource=resource,
                resource_id=resource_id,
                details=details or {},
                timestamp=datetime.utcnow()
            )
            session.add(log_entry)
            session.flush()
    except Exception as e:
        # Audit log failure should NEVER break the main request flow.
        logger.warning("Audit log write failed (non-fatal): %s", e)


def _dashboard_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """GET /dashboard – aggregate stats, patient queue, AI alerts (frontend shape)."""
    data = get_dashboard_data()
    return json_response(200, data, event=event)


def _terminology_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """GET /api/v1/terminology – approved medical terminology (Phase 3.4 / R7)."""
    try:
        from cdss.services.i18n import APPROVED_TERMINOLOGY, get_supported_languages
        payload = {
            "terminology": {k: v for k, v in APPROVED_TERMINOLOGY.items() if k != "en"},
            "languages": get_supported_languages(),
        }
        return json_response(200, payload, event=event)
    except Exception as e:
        logger.warning("Terminology handler failed: %s", e)
        return json_response(500, {"error": "Internal server error"}, event=event)


def _agent_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """POST /agent – delegate to Supervisor for intent-based routing."""
    try:
        from cdss.api.handlers.supervisor import handler as supervisor_handler
        return supervisor_handler(event, context)
    except Exception as e:
        logger.warning("Agent/Supervisor fallback: %s", e)
        # Fallback to simple chat if Supervisor fails
        body = {}
        try:
            raw = event.get("body")
            if raw:
                body = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
        user_message = (body.get("message") or body.get("prompt") or "").strip()
        history = body.get("history") or body.get("conversation") or []
        try:
            if history and isinstance(history, list) and len(history) > 0:
                from cdss.bedrock.chat import invoke_chat_multi_turn
                messages_list = list(history)
                messages_list.append({"role": "user", "text": user_message or "(No message)"})
                result = invoke_chat_multi_turn(messages_list)
            else:
                from cdss.bedrock.chat import invoke_chat
                result = invoke_chat(user_message)
            return json_response(
                200,
                {
                    "message": result.message or "OK",
                    "reply": result.reply,
                    "data": {"reply": result.reply, "safety_disclaimer": result.safety_disclaimer},
                    "safety_disclaimer": result.safety_disclaimer,
                },
                event=event,
            )
        except Exception:
            return json_response(
                200,
                {
                    "message": "Agent endpoint ready. Connect Bedrock for live responses.",
                    "reply": "Agent endpoint ready.",
                    "data": {"reply": "Agent endpoint ready.", "safety_disclaimer": "AI is not configured or unavailable."},
                    "safety_disclaimer": "AI is not configured or unavailable.",
                },
                event=event,
            )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        claims = _get_claims(event)
        role = _get_role(claims)
        user_id = _get_user_id(claims)
        email = _get_email(claims)

        method = (event.get("httpMethod") or event.get("requestMethod") or "GET").upper()
        path = event.get("path") or (event.get("requestContext") or {}).get("path") or "/api"
        resource = path


        # Direct routes: GET /docs/swagger.yaml, GET /health, GET /dashboard, POST /agent (no proxy)
        if path.rstrip("/") == "/docs/swagger.yaml" and method == "GET":
            return _serve_swagger_yaml(event)
        if (path.rstrip("/") == "/health" or path.rstrip("/") == "" or path.rstrip("/").endswith("/health")) and method == "GET":
            health_body = {"service": "cdss", "status": "ok", "user_id": user_id or "anonymous"}
            try:
                from cdss.db.session import get_session
                from sqlalchemy import text
                with get_session() as session:
                    session.execute(text("SELECT 1"))
                health_body["database"] = "connected"
            except Exception:
                health_body["database"] = "unavailable"
            return json_response(200, health_body, event=event)
        if path.rstrip("/").endswith("/dashboard"):
            if method == "GET":
                return _dashboard_handler(event, context)
            _audit_log(event, f"{method} {path}", resource, details={"status": 405})
            return json_response(
                405,
                {"error": "MethodNotAllowed", "message": "GET only"},
                event=event,
            )
        if path.rstrip("/").endswith("/agent"):
            if method == "POST":
                return _agent_handler(event, context)
            _audit_log(event, f"{method} {path}", resource, details={"status": 405})
            return json_response(
                405,
                {"error": "MethodNotAllowed", "message": "POST only"},
                event=event,
            )

        # RBAC: admin-only paths (admin and superuser allowed)
        if _path_requires_admin(path):
            if not _can_access_admin_paths(role):
                _audit_log(event, f"{method} {path}", resource, details={"status": 403, "reason": "AdminRequired"})
                return json_response(
                    403,
                    {"error": "Forbidden", "message": "Admin role required"},
                    event=event,
                )

        # Dispatch target (used for patient-scoped RBAC and routing)
        proxy = (event.get("pathParameters") or {}).get("proxy") or ""

        # Patient-scoped paths: role `patient` may only access their own record.
        # Superuser bypasses patient scoping (full access). Admin already can access all.
        if role == "patient" and not _is_superuser(role):
            # Normalize for patterns like "v1/patients" and "v1/patients/PT-1001"
            parts = [p for p in proxy.split("/") if p]
            # Block patient from list view of all patients
            if proxy in {"v1/patients", "patients"} or (
                len(parts) == 2
                and parts[0].lower() == "v1"
                and parts[1].lower() == "patients"
            ):
                _audit_log(event, f"{method} {path}", resource, details={"status": 403, "reason": "PatientBlockListView"})
                return json_response(
                    403,
                    {"error": "Forbidden", "message": "Patients may only access their own record."},
                    event=event,
                )

            # For patient detail routes, enforce id match
            patient_id_in_path = None
            if proxy.startswith("v1/patients"):
                # e.g. v1/patients/PT-1001
                if len(parts) >= 3 and parts[0].lower() == "v1" and parts[1].lower() == "patients":
                    patient_id_in_path = parts[2]
            elif proxy.startswith("patients"):
                # e.g. patients/PT-1001
                if len(parts) >= 2 and parts[0].lower() == "patients":
                    patient_id_in_path = parts[1]

            if patient_id_in_path:
                patient_id_claim = _get_patient_id(claims)
                if not patient_id_claim or patient_id_in_path != patient_id_claim:
                    _audit_log(event, f"{method} {path}", resource, details={"status": 403, "reason": "PatientScopeViolation", "path_id": patient_id_in_path})
                    return json_response(
                        403,
                        {"error": "Forbidden", "message": "Patients may only access their own record."},
                        event=event,
                    )

        # Audit successful access before dispatch
        _audit_log(event, f"{method} {path}", resource, details={"status": 200})

        # Dispatch to agent handlers by path
        if proxy == "docs" and method == "GET":
            return _serve_swagger_ui(event)
        if proxy.startswith("v1/patients") or proxy == "patients" or (proxy.startswith("patients/") and "/" in proxy):
            from cdss.api.handlers.patient import handler as patient_handler
            return patient_handler(event, context)
        if proxy.startswith("v1/admin"):
            from cdss.api.handlers.admin import handler as admin_handler
            return admin_handler(event, context)
        if proxy.startswith("v1/surgeries"):
            from cdss.api.handlers.surgery import handler as surgery_handler
            return surgery_handler(event, context)
        if proxy.startswith("v1/resources"):
            from cdss.api.handlers.resource import handler as resource_handler
            return resource_handler(event, context)
        if proxy.startswith("v1/medications") or proxy.startswith("v1/reminders"):
            from cdss.api.handlers.engagement import handler as engagement_handler
            return engagement_handler(event, context)
        if proxy.startswith("v1/consultations"):
            from cdss.api.handlers.engagement import handler as engagement_handler
            return engagement_handler(event, context)
        if proxy.startswith("v1/schedule"):
            from cdss.api.handlers.scheduling import handler as scheduling_handler
            return scheduling_handler(event, context)
        if proxy.startswith("v1/activity"):
            from cdss.api.handlers.activity import handler as activity_handler
            return activity_handler(event, context)
        if proxy.startswith("v1/hospitals"):
            from cdss.api.handlers.hospitals import hospitals_handler
            return hospitals_handler(event, context)
        if proxy == "v1/terminology" and method == "GET":
            return _terminology_handler(event)
        if proxy.startswith("v1/ai") or proxy.startswith("ai/"):
            from cdss.api.handlers.ai import handler as ai_handler
            return ai_handler(event, context)
        # NOTE: Triage route removed — CDSS uses 5 agents only (no Triage agent).
        if proxy.startswith("v1/supervisor"):
            from cdss.api.handlers.supervisor import handler as supervisor_handler
            return supervisor_handler(event, context)
        if proxy.startswith("v1/appointments"):
            from cdss.api.handlers.appointments import handler as appointments_handler
            return appointments_handler(event, context)
        if proxy.startswith("v1/tasks"):
            from cdss.api.handlers.tasks import handler as tasks_handler
            return tasks_handler(event, context)

        # Inject temporary seed route
        if proxy.startswith("v1/seed"):
            from cdss.db.seed import run_seed
            result = run_seed(force=True)
            return json_response(200, {"status": "seeded", "result": result}, event=event)

        # Default
        return json_response(
            200,
            {"service": "cdss", "status": "ok", "user_id": user_id or "anonymous"},
            event=event,
        )
    except Exception as e:
        logger.exception("Router error: %s", e)
        return json_response(
            500,
            {"error": "InternalServerError", "message": "Internal server error"},
            event=event,
        )
