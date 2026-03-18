#!/usr/bin/env python3
"""
Test CDSS API handlers locally (no AWS deploy needed).
Run from repo root: python scripts/test_api_local.py

Uses mock API Gateway events and optional Cognito-style claims.
When DATABASE_URL and RDS_CONFIG_SECRET_NAME are not set, get_session is mocked
so handlers return 200 with empty data (no real DB required).
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src so we can import cdss (works from any cwd when script path is absolute)
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Early import check with clear error
try:
    import cdss.api.handlers.router  # noqa: F401
except ModuleNotFoundError as e:
    print("Error: Could not import cdss.", file=sys.stderr)
    print("  Run from repo root:  cd D:\\AI_Hackathon_CDSS  then  python scripts/test_api_local.py", file=sys.stderr)
    print("  Or install the package:  pip install -e .", file=sys.stderr)
    print(f"  Detail: {e}", file=sys.stderr)
    sys.exit(1)


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


def make_event(path_proxy: str, method: str = "GET", claims: dict | None = None, body: dict | None = None):
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


def make_direct_event(path_suffix: str, method: str = "GET", body: dict | None = None, claims: dict | None = None):
    """Build event for direct routes like /dashboard and /agent (no proxy)."""
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


def main():
    use_db = bool(os.environ.get("DATABASE_URL") or os.environ.get("RDS_CONFIG_SECRET_NAME"))
    run_ctx = nullcontext() if use_db else _mock_get_session()

    if use_db:
        print("CDSS API – local handler test (using DATABASE_URL / RDS config)\n" + "=" * 50)
    else:
        print("CDSS API – local handler test (mocked DB; set DATABASE_URL for real DB)\n" + "=" * 50)

    admin_claims = {
        "sub": "admin-1",
        "email": "admin@cdss.ai",
        "custom:role": "admin",
        "cognito:username": "admin@cdss.ai",
    }
    doctor_claims = {
        "sub": "doc-1",
        "email": "priya@cdss.ai",
        "custom:role": "doctor",
        "cognito:username": "priya@cdss.ai",
    }

    tests = [
        ("GET /api/v1/patients", make_event("v1/patients", "GET", doctor_claims)),
        ("GET /api/v1/patients/PT-1001", make_event("v1/patients/PT-1001", "GET", doctor_claims)),
        ("GET /api/v1/surgeries", make_event("v1/surgeries", "GET", doctor_claims)),
        ("GET /api/v1/surgeries/SRG-001", make_event("v1/surgeries/SRG-001", "GET", doctor_claims)),
        ("GET /api/v1/resources", make_event("v1/resources", "GET", doctor_claims)),
        ("GET /api/v1/medications", make_event("v1/medications", "GET", doctor_claims)),
        ("GET /api/v1/schedule", make_event("v1/schedule", "GET", doctor_claims)),
        ("POST /api/v1/reminders/nudge", make_event("v1/reminders/nudge", "POST", doctor_claims, {"patient_id": "PT-1"})),
        ("POST /api/v1/consultations/start", make_event("v1/consultations/start", "POST", doctor_claims, {"patient_id": "PT-1", "doctor_id": "DOC-1"})),
        ("POST /api/v1/consultations", make_event("v1/consultations", "POST", doctor_claims, {"patient_id": "PT-1", "notes": "Test"})),
        ("GET /api/v1/admin/audit", make_event("v1/admin/audit", "GET", admin_claims)),
        ("GET /api/v1/admin/users", make_event("v1/admin/users", "GET", admin_claims)),
        ("GET /api/v1/admin/config", make_event("v1/admin/config", "GET", admin_claims)),
        ("GET /api/v1/admin/analytics", make_event("v1/admin/analytics", "GET", admin_claims)),
        ("GET /api/v1/admin/resources", make_event("v1/admin/resources", "GET", admin_claims)),
        ("GET /dashboard", make_direct_event("dashboard", "GET", claims=doctor_claims)),
        ("POST /agent", make_direct_event("agent", "POST", body={"message": "hello"}, claims=doctor_claims)),
    ]

    passed = 0
    failed = 0
    with run_ctx:
        from cdss.api.handlers.router import handler as router_handler

        for label, event in tests:
            try:
                result = router_handler(event, None)
                status = result.get("statusCode", "?")
                body = result.get("body", "{}")
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except Exception:
                        pass
                body_str = json.dumps(body)
                body_preview = body_str[:200] + ("..." if len(body_str) > 200 else "")
                ok = 200 <= int(status) < 300 if str(status).isdigit() else False
                if not ok and str(status) == "404" and isinstance(body, dict) and "not found" in str(body.get("error", "")).lower():
                    ok = True  # 404 Not found expected with empty DB
                if ok:
                    passed += 1
                else:
                    failed += 1
                print(f"\n{label}")
                print(f"  Status: {status} {'OK' if ok else 'FAIL'}")
                print(f"  Body:   {body_preview}")
            except Exception as e:
                failed += 1
                print(f"\n{label}")
                print(f"  ERROR: {e}")
                err_str = str(e).lower()
                if "connection refused" in err_str or "connection timed out" in err_str or "password authentication failed" in err_str:
                    print("  Hint: DATABASE_URL is set but DB may be unreachable. Start SSM tunnel or check URL.", file=sys.stderr)
                if "no module named 'cdss'" in err_str or "modulenotfounderror" in err_str:
                    print("  Hint: Run from repo root (D:\\AI_Hackathon_CDSS) or run: pip install -e .", file=sys.stderr)
    print("\n" + "=" * 50)
    print(f"Done. Passed: {passed}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
