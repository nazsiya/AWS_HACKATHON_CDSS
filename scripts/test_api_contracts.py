#!/usr/bin/env python3
"""
Contract tests for key CDSS REST endpoints.

Focus:
- GET /dashboard
- GET /api/v1/schedule
- POST /api/v1/activity

Run from repo root:
  python scripts/test_api_contracts.py
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict

from unittest.mock import MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _mock_session():
    """Build a mock session that returns empty results for all queries."""
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    session.scalars.return_value.__iter__ = lambda self: iter([])
    session.scalar.return_value = None
    session.execute.return_value.all.return_value = []
    session.execute.return_value.first.return_value = None
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@contextmanager
def _mock_get_session():
    """Context manager that patches get_session to yield a mock session (no DB)."""
    mock_sess = _mock_session()

    @contextmanager
    def fake_cm():
        yield mock_sess

    def fake_get_session(secret_name=None):
        return fake_cm()

    with patch("cdss.db.session.get_session", fake_get_session):
        yield


def make_event(path_proxy: str, method: str = "GET", claims: Dict[str, Any] | None = None, body: Dict[str, Any] | None = None):
    claims = claims or {}
    return {
        "httpMethod": method,
        "path": f"/dev/api/{path_proxy}",
        "pathParameters": {"proxy": path_proxy},
        "requestContext": {
            "path": f"/dev/api/{path_proxy}",
            "authorizer": {"claims": claims} if claims else {},
        },
        "body": json.dumps(body) if body is not None else None,
        "queryStringParameters": None,
    }


def make_direct_event(path_suffix: str, method: str = "GET", body: Dict[str, Any] | None = None, claims: Dict[str, Any] | None = None):
    claims = claims or {}
    path = f"/dev/{path_suffix.lstrip('/')}"
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": None,
        "requestContext": {
            "path": path,
            "authorizer": {"claims": claims} if claims else {},
        },
        "body": json.dumps(body) if body is not None else None,
        "queryStringParameters": None,
    }


def _load_body(result: Dict[str, Any]) -> Dict[str, Any]:
    body = result.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {}
    return body or {}


def test_dashboard_contract(router_handler, doctor_claims) -> None:
    event = make_direct_event("dashboard", "GET", claims=doctor_claims)
    result = router_handler(event, None)
    assert result.get("statusCode") == 200, f"/dashboard expected 200, got {result.get('statusCode')}"
    body = _load_body(result)

    assert isinstance(body.get("stats"), dict), "dashboard.stats must be an object"
    stats = body["stats"]
    for key in ("totalPatients", "activeSurgeries", "alertsCount"):
        assert key in stats, f"dashboard.stats missing key: {key}"
        assert isinstance(stats[key], int), f"dashboard.stats.{key} must be int"

    assert isinstance(body.get("patientQueue"), list), "dashboard.patientQueue must be a list"
    assert isinstance(body.get("aiAlerts"), list), "dashboard.aiAlerts must be a list"
    assert isinstance(body.get("recentActivity"), list), "dashboard.recentActivity must be a list"


def test_schedule_contract(router_handler, doctor_claims) -> None:
    event = make_event("v1/schedule", "GET", claims=doctor_claims)
    result = router_handler(event, None)
    assert result.get("statusCode") == 200, f"/api/v1/schedule expected 200, got {result.get('statusCode')}"
    body = _load_body(result)

    assert "schedule" in body, "schedule response must have 'schedule' key"
    assert isinstance(body["schedule"], list), "schedule must be a list"
    # When items exist, they must have at least the documented fields plus type for frontend.
    for item in body["schedule"]:
        for key in ("id", "ot", "date", "time", "surgeryId", "patient", "status", "type"):
            assert key in item, f"schedule item missing key: {key}"


def test_activity_contract(router_handler, doctor_claims) -> None:
    body = {
        "doctor_id": doctor_claims["sub"],
        "action": "view_dashboard",
        "patient_id": "PT-TEST",
        "resource": "/dashboard",
        "detail": "Viewed dashboard in contract test",
    }
    event = make_event("v1/activity", "POST", claims=doctor_claims, body=body)
    result = router_handler(event, None)
    assert result.get("statusCode") == 201, f"/api/v1/activity expected 201, got {result.get('statusCode')}"
    resp_body = _load_body(result)
    assert resp_body.get("ok") is True, "activity response must include ok=true"
    assert resp_body.get("doctor_id") == body["doctor_id"], "activity doctor_id must echo request"


def main() -> int:
    from cdss.api.handlers.router import handler as router_handler

    doctor_claims = {
        "sub": "doc-contract",
        "email": "doctor.contract@cdss.ai",
        "custom:role": "doctor",
        "cognito:username": "doctor.contract@cdss.ai",
    }

    with _mock_get_session():
        tests = [
            ("Dashboard contract", test_dashboard_contract),
            ("/api/v1/schedule contract", test_schedule_contract),
            ("/api/v1/activity contract", test_activity_contract),
        ]
        failures = 0
        for label, fn in tests:
            try:
                fn(router_handler, doctor_claims)
                print(f"[OK] {label}")
            except AssertionError as exc:
                failures += 1
                print(f"[FAIL] {label}: {exc}")

    if failures:
        print(f"\nContract tests failed: {failures}", file=sys.stderr)
        return 1
    print("\nAll contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

