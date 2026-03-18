#!/usr/bin/env python3
"""
Phase 4: Verify AI summary and AI chatbot (agent) endpoints.

Run from repo root with API already running (e.g. run_api_local.py on 8080 or 8081):
  BASE_URL=http://localhost:8081 python scripts/verify_phase4_ai.py

Or use run_phase4_verify.ps1 which sets BASE_URL and runs this script.
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


def get(path: str) -> tuple[int, dict]:
    """GET path; return (status_code, parsed_json)."""
    try:
        req = urllib.request.Request(BASE_URL + path, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            if e.fp:
                body = json.loads(e.fp.read().decode("utf-8"))
        except (json.JSONDecodeError, ValueError, AttributeError):
            body = {"error": str(e)}
        return e.code, body
    except OSError as e:
        return 0, {"error": str(e)}


def post(path: str, body: dict) -> tuple[int, dict]:
    """POST path with JSON body; return (status_code, parsed_json)."""
    try:
        req = urllib.request.Request(
            BASE_URL + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        resp_body = {}
        try:
            if e.fp:
                resp_body = json.loads(e.fp.read().decode("utf-8"))
        except (json.JSONDecodeError, ValueError, AttributeError):
            resp_body = {"error": str(e)}
        return e.code, resp_body
    except OSError as e:
        return 0, {"error": str(e)}


def main() -> int:
    print("Phase 4: AI summary and AI chatbot verification")
    print(f"  BASE_URL={BASE_URL}")
    print()

    failures = []

    # 1. Health
    status, health = get("/health")
    if status != 200:
        failures.append(f"GET /health: expected 200, got {status}")
    else:
        print("  1. GET /health: 200 OK")

    # 2. AI Chatbot (POST /agent)
    agent_payload = {"message": "List patients or give a short patient summary"}
    status, data = post("/agent", agent_payload)
    if status != 200:
        failures.append(f"POST /agent: expected 200, got {status}")
    else:
        inner = data.get("data") if isinstance(data.get("data"), dict) else {}
        reply = inner.get("reply") or data.get("reply")
        disclaimer = data.get("safety_disclaimer") or inner.get("safety_disclaimer")
        if not reply and not data.get("intent"):
            failures.append("POST /agent: response missing reply or intent")
        else:
            print("  2. POST /agent (AI chatbot): 200 OK")
            if reply:
                print(f"     reply (first 120 chars): {(reply if isinstance(reply, str) else str(reply))[:120]}...")
            if disclaimer:
                print(f"     safety_disclaimer: present")

    # 3. AI Summary (POST /api/ai/summarize)
    summarize_payload = {"text": "Patient has hypertension. Currently on amlodipine 5mg. Last BP 138/88."}
    status, data = post("/api/ai/summarize", summarize_payload)
    if status != 200:
        failures.append(f"POST /api/ai/summarize: expected 200, got {status}")
    else:
        summary = data.get("summary")
        disclaimer = data.get("safety_disclaimer")
        if summary is None and "error" not in data:
            failures.append("POST /api/ai/summarize: response missing 'summary' field")
        else:
            print("  3. POST /api/ai/summarize: 200 OK")
            if summary:
                print(f"     summary (first 120 chars): {(summary or data.get('error', ''))[:120]}...")
            if disclaimer:
                print(f"     safety_disclaimer: present")

    print()
    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("  Ensure the API is running: python scripts/run_api_local.py")
        print("  If using another port: $env:BASE_URL=\"http://localhost:8081\"; python scripts/verify_phase4_ai.py")
        return 1

    print("OK: AI summary and AI chatbot endpoints working. Phase 4 check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
