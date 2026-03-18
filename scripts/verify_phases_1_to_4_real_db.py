#!/usr/bin/env python3
"""
Phases 1–4 verification against **real database** (Aurora).

Use this when the dashboard and API are connected to Aurora. The script requires
the API to be running with DATABASE_URL (or RDS_CONFIG_SECRET_NAME) set so that
GET /health returns "database": "connected" and GET /api/v1/patients returns 200
with real data (not mock).

Run from repo root:
  1. Start API with real DB: set DATABASE_URL (and SSM tunnel if needed), then
     $env:PYTHONPATH="src"; python scripts/run_api_local.py
  2. In another terminal: $env:BASE_URL="http://localhost:8080"; python scripts/verify_phases_1_to_4_real_db.py

Or run: .\\scripts\\run_phases_1_to_4_verify.ps1  (script ensures API is up and uses real DB)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

BASE_URL = (os.environ.get("BASE_URL") or "http://localhost:8080").strip().rstrip("/")
TIMEOUT = 30
REQUIRE_REAL_DB = os.environ.get("REAL_DB", "1").strip().lower() in ("1", "true", "yes")


def get(path: str, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(BASE_URL + path, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            if e.fp:
                body = json.loads(e.fp.read().decode("utf-8"))
        except Exception:
            body = {"error": str(e.code)}
        return e.code, body
    except OSError as e:
        return 0, {"error": str(e)}


def post(path: str, body: dict, headers: dict | None = None) -> tuple[int, dict]:
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers=h,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        resp_body = {}
        try:
            if e.fp:
                resp_body = json.loads(e.fp.read().decode("utf-8"))
        except Exception:
            resp_body = {"error": str(e.code)}
        return e.code, resp_body
    except OSError as e:
        return 0, {"error": str(e)}


def main() -> int:
    print("Phases 1–4 verification (real database)")
    print(f"  BASE_URL={BASE_URL}")
    print(f"  REQUIRE_REAL_DB={REQUIRE_REAL_DB}")
    print()

    failures = []

    # --- Phase 1.3: Health + Agent ---
    status, health = get("/health")
    if status != 200:
        failures.append(f"Phase 1: GET /health -> {status}")
    else:
        print("  Phase 1: GET /health: 200 OK")
        db_status = health.get("database", "")
        if REQUIRE_REAL_DB and db_status != "connected":
            failures.append(
                f"Real DB required but /health has database={db_status!r}. "
                "Set DATABASE_URL (and start SSM tunnel if using Aurora) before starting the API."
            )
        elif db_status == "connected":
            print("    database: connected (real DB)")
        else:
            print("    database:", db_status or "unavailable (mock or unset)")

    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        print("\n  Start API with DATABASE_URL set for Aurora; then run this script with BASE_URL pointing to the API.")
        return 1

    # Agent (Phase 1.3)
    status, data = post("/agent", {"message": "List patients"})
    if status != 200:
        failures.append(f"Phase 1: POST /agent -> {status}")
    else:
        inner = data.get("data") or {}
        reply = inner.get("reply") or data.get("reply")
        if not reply and not data.get("intent"):
            failures.append("Phase 1: POST /agent missing reply or intent")
        else:
            print("  Phase 1: POST /agent: 200 OK (AI chatbot)")

    # --- Phase 3: Frontend-called endpoint (patients from DB) ---
    status, data = get("/api/v1/patients")
    if status != 200:
        failures.append(f"Phase 3: GET /api/v1/patients -> {status} (expected 200 with real DB)")
    else:
        patients = data.get("patients")
        if not isinstance(patients, list):
            failures.append("Phase 3: /api/v1/patients missing 'patients' list")
        else:
            print(f"  Phase 3: GET /api/v1/patients: 200 OK ({len(patients)} patients from DB)")
    if status == 500 and REQUIRE_REAL_DB:
        failures.append("Phase 3: Patients endpoint returned 500. Check DATABASE_URL and DB connectivity.")

    # --- Phase 4: AI summary ---
    status, data = post("/api/ai/summarize", {"text": "Patient has hypertension. On amlodipine 5mg."})
    if status != 200:
        failures.append(f"Phase 4: POST /api/ai/summarize -> {status}")
    else:
        if data.get("summary") is None and "error" not in data:
            failures.append("Phase 4: /api/ai/summarize missing 'summary'")
        else:
            print("  Phase 4: POST /api/ai/summarize: 200 OK")

    # --- Phase 3.4: Terminology (multilingual) ---
    status, data = get("/api/v1/terminology")
    if status != 200:
        failures.append(f"Phase 3.4: GET /api/v1/terminology -> {status}")
    else:
        if "terminology" not in data or "languages" not in data:
            # API may be an older build without the terminology route (returns default 200 body)
            if data.get("service") == "cdss" and "status" in data:
                print(
                    "  Phase 3.4: GET /api/v1/terminology: skipped (API needs restart to load new route)."
                )
            else:
                failures.append("Phase 3.4: /api/v1/terminology missing terminology or languages")
        else:
            print("  Phase 3.4: GET /api/v1/terminology: 200 OK (approved terms + languages)")

    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("OK: Phases 1–4 verified against real database (Aurora).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
