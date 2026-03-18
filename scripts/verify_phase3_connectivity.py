#!/usr/bin/env python3
"""
Phase 3: Quick frontend-backend connectivity check (no agent call).
Tests GET /health and GET /api/v1/patients. Run with API already up.
  BASE_URL=http://localhost:8081 python scripts/verify_phase3_connectivity.py

For real database verification (Aurora): set REAL_DB=1. Then the script requires
GET /health to return database=connected and GET /api/v1/patients to return 200.
  REAL_DB=1 BASE_URL=http://localhost:8080 python scripts/verify_phase3_connectivity.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE_URL = (os.environ.get("BASE_URL") or "http://localhost:8080").strip().rstrip("/")
TIMEOUT = 20
REQUIRE_REAL_DB = os.environ.get("REAL_DB", "").strip().lower() in ("1", "true", "yes")


def get(path: str) -> tuple[int, dict]:
    try:
        req = urllib.request.Request(BASE_URL + path, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            raw = f.read().decode("utf-8")
            return f.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.fp.read().decode("utf-8")) if e.fp else {}
        except Exception:
            body = {"error": str(e.code)}
        return e.code, body
    except OSError as e:
        return 0, {"error": str(e)}


def main() -> int:
    print("Phase 3: Frontend–backend connectivity")
    print(f"  BASE_URL={BASE_URL}")
    if REQUIRE_REAL_DB:
        print("  REAL_DB=1 (require database connected and patients 200)")
    print()

    # 1. Health
    status, data = get("/health")
    if status != 200:
        print(f"FAIL: GET /health -> {status}", data)
        return 1
    if data.get("service") != "cdss":
        print("FAIL: /health response missing service=cdss", data)
        return 1
    print("  GET /health: 200 OK (service=cdss)")
    db_status = data.get("database", "")
    if REQUIRE_REAL_DB and db_status != "connected":
        print("FAIL: Real DB required but database=%r. Set DATABASE_URL and start API." % db_status)
        return 1
    if db_status:
        print("    database:", db_status)

    # 2. Patients list (frontend-called endpoint)
    status, data = get("/api/v1/patients")
    if status not in (200, 500):
        print(f"FAIL: GET /api/v1/patients -> {status}", data)
        return 1
    if status == 500:
        print("  GET /api/v1/patients: 500 (API reachable; DB may be down or misconfigured).")
        if REQUIRE_REAL_DB:
            print("FAIL: REAL_DB=1 but patients returned 500. Fix DATABASE_URL and DB connectivity.")
            return 1
        print("  For full pass: start API with DATABASE_URL unset (mock) or with a running DB.")
        print()
        print("PARTIAL: Phase 3 API and frontend endpoint are reachable; patients list requires DB or mock.")
        return 0
    patients = data.get("patients")
    if not isinstance(patients, list):
        print("FAIL: /api/v1/patients response missing 'patients' list", list(data.keys()))
        return 1
    print(f"  GET /api/v1/patients: 200 OK ({len(patients)} patients)")
    print()
    print("OK: Phase 3 connectivity verified (API + frontend-called endpoint).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
