#!/usr/bin/env python3
"""
Verify CDSS API and connectivity: API handlers, DB (optional), Bedrock (optional).

Run from repo root:
  PYTHONPATH=src python scripts/check_connectivity.py

With DATABASE_URL set (and tunnel if using Aurora), DB is tested.
With BEDROCK_CONFIG_SECRET_NAME set, Bedrock + Secrets Manager are tested.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_api_tests() -> tuple[int, int]:
    """Run test_api_local style checks; return (passed, failed)."""
    from contextlib import contextmanager, nullcontext
    from unittest.mock import MagicMock, patch

    def _mock_session():
        session = MagicMock()
        session.scalars.return_value.all.return_value = []
        session.scalars.return_value.__iter__ = lambda self: iter([])
        session.scalar.return_value = None
        session.execute.return_value.all.return_value = []
        session.execute.return_value.first.return_value = None
        session.add = MagicMock()
        session.flush = MagicMock()
        return session

    @contextmanager
    def _mock_get_session():
        mock_sess = _mock_session()
        @contextmanager
        def fake_cm():
            yield mock_sess
        with patch("cdss.db.session.get_session", lambda secret_name=None: fake_cm()):
            yield

    use_db = bool(os.environ.get("DATABASE_URL") or os.environ.get("RDS_CONFIG_SECRET_NAME"))
    run_ctx = nullcontext() if use_db else _mock_get_session()

    doctor_claims = {"sub": "doc-1", "custom:role": "doctor"}

    events = [
        ("GET /api/v1/patients", "GET", "v1/patients", doctor_claims, None),
        ("GET /api/v1/surgeries", "GET", "v1/surgeries", doctor_claims, None),
        ("GET /dashboard", "GET", None, doctor_claims, None),
        ("POST /agent", "POST", None, doctor_claims, {"message": "hello"}),
    ]

    passed = failed = 0
    with run_ctx:
        from cdss.api.handlers.router import handler as router_handler

        for label, method, proxy, claims, body in events:
            if proxy:
                event = {
                    "httpMethod": method,
                    "path": f"/dev/api/{proxy}",
                    "pathParameters": {"proxy": proxy},
                    "requestContext": {"authorizer": {"claims": claims}},
                    "body": json.dumps(body) if body else None,
                    "queryStringParameters": None,
                }
            else:
                path = "dashboard" if "dashboard" in label else "agent"
                event = {
                    "httpMethod": method,
                    "path": f"/dev/{path}",
                    "pathParameters": None,
                    "requestContext": {"authorizer": {"claims": claims}},
                    "body": json.dumps(body) if body else None,
                    "queryStringParameters": None,
                }
            try:
                result = router_handler(event, None)
                status = result.get("statusCode", 500)
                ok = 200 <= int(status) < 300
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
    return passed, failed


def check_db() -> tuple[bool, str]:
    """Try one get_session() and a simple query. Returns (ok, message)."""
    if not os.environ.get("DATABASE_URL") and not os.environ.get("RDS_CONFIG_SECRET_NAME"):
        return True, "skipped (no DATABASE_URL / RDS_CONFIG_SECRET_NAME)"
    try:
        from cdss.db.session import get_session
        from sqlalchemy import text
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, str(e)


def check_bedrock() -> tuple[bool, str]:
    """Try load Bedrock config from Secrets Manager and one Converse call. Returns (ok, message)."""
    secret = os.environ.get("BEDROCK_CONFIG_SECRET_NAME")
    if not secret:
        return True, "skipped (no BEDROCK_CONFIG_SECRET_NAME)"
    try:
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret)
        config = json.loads(resp.get("SecretString", "{}"))
        model_id = config.get("model_id") or "anthropic.claude-3-haiku-20240307-v1:0"
        br_region = config.get("region") or region
        br = boto3.client("bedrock-runtime", region_name=br_region)
        br.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "Say OK only."}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        return True, "ok"
    except Exception as e:
        return False, str(e)


def main() -> int:
    print("CDSS connectivity check")
    print("=" * 50)

    # 1. API
    print("\n1. API handlers (router)")
    try:
        p, f = run_api_tests()
        if f == 0:
            print(f"   OK – {p} requests passed")
        else:
            print(f"   FAIL – {p} passed, {f} failed")
            return 1
    except Exception as e:
        print(f"   ERROR – {e}")
        return 1

    # 2. DB
    print("\n2. Database (Aurora / PostgreSQL)")
    db_ok, db_msg = check_db()
    if db_ok:
        print(f"   {db_msg}")
    else:
        print(f"   FAIL – {db_msg}")
        if "connect" in db_msg.lower() or "refused" in db_msg.lower() or "timeout" in db_msg.lower():
            print("   Hint: Start SSM tunnel and set DATABASE_URL=postgresql://...@localhost:5433/cdssdb")

    # 3. Bedrock
    print("\n3. Bedrock + Secrets Manager")
    br_ok, br_msg = check_bedrock()
    if br_ok:
        print(f"   {br_msg}")
    else:
        print(f"   FAIL – {br_msg}")
        print("   Hint: Set BEDROCK_CONFIG_SECRET_NAME and ensure AWS credentials can read the secret and invoke Bedrock")

    print("\n" + "=" * 50)
    if db_ok and br_ok:
        print("All connectivity checks passed or skipped.")
    else:
        print("Some checks failed (see above). API tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
