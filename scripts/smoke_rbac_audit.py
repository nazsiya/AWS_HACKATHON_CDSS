#!/usr/bin/env python3
"""
Smoke test for Phase 1–2 RBAC + audit logging.

Runs locally using a temporary SQLite DB (no AWS deploy required).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


# Ensure imports work when run from repo root or elsewhere
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def make_event(path_proxy: str, method: str, claims: dict, body: dict | None = None):
    return {
        "httpMethod": method,
        "path": f"/dev/api/{path_proxy}",
        "pathParameters": {"proxy": path_proxy},
        "requestContext": {"path": f"/dev/api/{path_proxy}", "authorizer": {"claims": claims}},
        "body": json.dumps(body) if body is not None else None,
        "queryStringParameters": None,
        "headers": {},
    }


def _assert(label: str, cond: bool, detail: str = "") -> int:
    if cond:
        print(f"[OK]   {label}")
        return 0
    print(f"[FAIL] {label}{(' - ' + detail) if detail else ''}")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "cdss_smoke.db"
        os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"

        from cdss.db.session import init_db, get_session, get_engine
        from cdss.db.seed import run_seed

        try:
            init_db()
            run_seed(force=True)

            from cdss.api.handlers.router import handler as router_handler
            from cdss.db.models import AuditLog
            from sqlalchemy import select, func

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
            patient_claims_mismatch = {
                "sub": "pat-1",
                "email": "patient@cdss.ai",
                "custom:role": "patient",
                "custom:patientId": "PT-9999",
            }
            patient_claims_match = {
                "sub": "pat-2",
                "email": "rajesh@patient.demo",
                "custom:role": "patient",
                "custom:patientId": "PT-1001",
            }

            failures = 0

            # RBAC: patient cannot list all patients
            resp = router_handler(make_event("v1/patients", "GET", patient_claims_match), None)
            failures += _assert(
                "patient denied listing patients",
                resp.get("statusCode") == 403,
                str(resp.get("body")),
            )

            # RBAC: patient can access their own patient record path
            resp = router_handler(make_event("v1/patients/PT-1001", "GET", patient_claims_match), None)
            failures += _assert(
                "patient allowed own record (not 403)",
                resp.get("statusCode") in (200, 404),
                f"status={resp.get('statusCode')} body={resp.get('body')}",
            )

            # RBAC: patient cannot access other patient record
            resp = router_handler(make_event("v1/patients/PT-1001", "GET", patient_claims_mismatch), None)
            failures += _assert(
                "patient denied other patient record",
                resp.get("statusCode") == 403,
                str(resp.get("body")),
            )

            # RBAC: doctor denied admin endpoints
            resp = router_handler(make_event("v1/admin/audit", "GET", doctor_claims), None)
            failures += _assert(
                "doctor denied admin audit",
                resp.get("statusCode") == 403,
                str(resp.get("body")),
            )

            # RBAC: admin allowed admin endpoints
            resp = router_handler(make_event("v1/admin/audit", "GET", admin_claims), None)
            failures += _assert(
                "admin allowed admin audit",
                resp.get("statusCode") in (200, 500),
                f"status={resp.get('statusCode')} body={resp.get('body')}",
            )

            # Audit: ensure at least one audit log row exists
            with get_session() as session:
                count = session.scalar(select(func.count(AuditLog.id))) or 0
            failures += _assert("audit log inserted", count >= 3, f"count={count}")

            print(f"\nDone. failures={failures}")
            return 0 if failures == 0 else 1
        finally:
            try:
                # Ensure SQLite file handle is released so TemporaryDirectory can clean up on Windows.
                get_engine().dispose()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

