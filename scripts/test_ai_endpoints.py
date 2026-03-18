#!/usr/bin/env python3
"""
Test AI endpoints from local PowerShell.

Usage:
  cd D:\AI_Hackathon_CDSS
  $env:PYTHONPATH="src"; python scripts\test_ai_endpoints.py

Tests:
  1. AI Chat         - POST /agent  (no DB needed, calls Bedrock)
  2. AI Summarize    - POST /ai/summarize  (no DB needed, calls Bedrock)
  3. AI Entities     - POST /ai/entities  (no DB needed, calls Bedrock)
  4. Consultation    - POST /consultations/start  (needs DB mock + Bedrock)
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up paths
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except ImportError:
    pass

# ---- helpers ----

def _make_event(method: str, path: str, proxy: str | None, body: dict | None = None) -> dict:
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"proxy": proxy} if proxy else None,
        "headers": {"Content-Type": "application/json"},
        "requestContext": {
            "path": path,
            "authorizer": {
                "claims": {
                    "custom:role": "doctor",
                    "sub": "local-test",
                    "email": "doctor@test.local",
                    "name": "Test Doctor"
                }
            }
        },
        "body": json.dumps(body) if body else None,
        "queryStringParameters": None,
    }


def _call(label: str, event: dict, use_mock_db: bool = False):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    try:
        from cdss.api.handlers.router import handler

        if use_mock_db:
            with _mock_db():
                result = handler(event, None)
        else:
            result = handler(event, None)

        status = result.get("statusCode", "?")
        body = json.loads(result.get("body", "{}"))
        print(f"  Status: {status}")

        if status == 200:
            # Print the body nicely, truncated
            nice = json.dumps(body, indent=2, ensure_ascii=False)
            if len(nice) > 600:
                nice = nice[:600] + "\n  ... (truncated)"
            print(f"  Response:\n{nice}")
        else:
            print(f"  Error: {json.dumps(body, indent=2)[:500]}")

        return status, body
    except Exception:
        traceback.print_exc()
        return 0, {}


# ---- mock DB for consultation test ----

@contextmanager
def _mock_db():
    """Lightweight mock for get_session so consultation start works without Aurora."""
    import datetime as dt

    class FakePatient:
        id = "PT-1001"
        name = "Rajesh Kumar"
        date_of_birth = dt.date(1980, 5, 20)
        gender = "M"
        conditions = ["Hypertension", "Type 2 Diabetes"]
        blood_group = "B+"
        severity = "moderate"
        status = "active"
        vitals = {"bp": "148/92", "hr": 78}
        allergies = []
        surgery_readiness = None

    class FakeVisit:
        _counter = 0
        def __init__(self, **kw):
            FakeVisit._counter += 1
            self.id = FakeVisit._counter
            for k, v in kw.items():
                setattr(self, k, v)
            if not hasattr(self, "notes"):
                self.notes = None
            if not hasattr(self, "summary"):
                self.summary = None
            if not hasattr(self, "extracted_entities"):
                self.extracted_entities = None
            if not hasattr(self, "transcript_s3_key"):
                self.transcript_s3_key = None
            if not hasattr(self, "created_at"):
                self.created_at = dt.datetime.now(dt.timezone.utc)

    patients = [FakePatient()]
    visits = []

    session = MagicMock()

    def fake_add(obj):
        if hasattr(obj, "patient_id"):
            visits.append(obj)
    session.add.side_effect = fake_add
    session.flush.return_value = None

    def fake_get(model_class, ident):
        for p in patients:
            if p.id == ident:
                return p
        return None
    session.get.side_effect = fake_get

    def fake_scalars(stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = visits[-5:]
        return mock_result
    session.scalars.side_effect = fake_scalars

    def fake_scalar(stmt):
        return None
    session.scalar.side_effect = fake_scalar

    def fake_execute(stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.first.return_value = None
        return mock_result
    session.execute.side_effect = fake_execute

    @contextmanager
    def fake_cm():
        yield session

    def fake_get_session(secret_name=None):
        return fake_cm()

    # Patch Visit constructor to use our FakeVisit
    import cdss.db.models as models
    original_visit = models.Visit

    with patch("cdss.db.session.get_session", fake_get_session), \
         patch("cdss.api.handlers.engagement.get_session", fake_get_session), \
         patch("cdss.api.handlers.patient.get_session", fake_get_session), \
         patch("cdss.db.models.Visit", FakeVisit), \
         patch("cdss.api.handlers.engagement.Visit", FakeVisit):
        yield

    models.Visit = original_visit


# ---- main ----

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  CDSS AI Feature Test Suite")
    print("=" * 60)

    results = {}

    # Test 1: AI Chat (uses Bedrock, no DB)
    event = _make_event("POST", "/api/agent", None,
                        {"message": "What are the warning signs of hypertension?"})
    s, b = _call("TEST 1: AI Chat (POST /agent)", event)
    results["AI Chat"] = "PASS" if s == 200 and (b.get("reply") or b.get("message") or b.get("response")) else "FAIL"

    # Test 2: AI Summarize (uses Bedrock, no DB)
    event = _make_event("POST", "/api/v1/ai/summarize", "v1/ai/summarize", {
        "text": (
            "Patient Rajesh Kumar, 45M, presents with persistent hypertension (BP 148/92). "
            "History of Type 2 Diabetes (HbA1c 7.8%). Currently on Metformin 500mg BD, "
            "Amlodipine 5mg OD. Reports dizziness and fatigue. Knee pain worsening. "
            "Plan: increase Amlodipine to 10mg, add Losartan 50mg. Follow-up 2 weeks."
        )
    })
    s, b = _call("TEST 2: AI Summarize (POST /ai/summarize)", event)
    results["AI Summarize"] = "PASS" if s == 200 else "FAIL"

    # Test 3: AI Entity Extraction (uses Bedrock, no DB)
    event = _make_event("POST", "/api/v1/ai/entities", "v1/ai/entities", {
        "text": (
            "Patient has hypertension and Type 2 Diabetes. Currently taking Metformin 500mg "
            "and Amlodipine 5mg. Allergic to Penicillin. Recommend adding Losartan 50mg."
        )
    })
    s, b = _call("TEST 3: AI Entity Extraction (POST /ai/entities)", event)
    results["AI Entities"] = "PASS" if s == 200 else "FAIL"

    # Test 4: Consultation Start (uses Bedrock + DB mock)
    event = _make_event("POST", "/api/v1/consultations/start", "v1/consultations/start", {
        "patient_id": "PT-1001",
        "doctor_id": "DOC-001"
    })
    s, b = _call("TEST 4: Consultation Start (POST /consultations/start) [mock DB]", event, use_mock_db=True)
    results["Consultation Start"] = "PASS" if s == 200 and b.get("visitId") else "FAIL"

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        icon = "✅" if result == "PASS" else "❌"
        print(f"  {icon}  {name}: {result}")
    print("=" * 60)

    all_pass = all(r == "PASS" for r in results.values())
    sys.exit(0 if all_pass else 1)
