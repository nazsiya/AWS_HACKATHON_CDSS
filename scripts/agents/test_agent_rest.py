#!/usr/bin/env python3
"""
REST POST /agent integration tests — source of truth for frontend.

Tests POST /agent with scenarios mapping to intents (patient summary, surgery planning,
resources, scheduling, engagement). Validates response envelope: intent, agent, data,
safety_disclaimer, correlationId. Validates safe fallback when Bedrock is unavailable.

Usage:
  # Against local server (scripts/run_api_local.py) or deployed API
  BASE_URL=http://localhost:8080 python scripts/agents/test_agent_rest.py

  # With mocked DB (no DATABASE_URL)
  PYTHONPATH=src python scripts/agents/test_agent_rest.py
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

BASE_URL = (os.environ.get("BASE_URL") or "").strip()
USE_HTTP = bool(BASE_URL)

# When BASE_URL is set but server is not reachable, fall back to handler for this run
_http_unavailable = False


def _mock_session():
    from unittest.mock import MagicMock
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
    @contextmanager
    def fake_cm():
        yield _mock_session()
    with patch("cdss.db.session.get_session", lambda secret_name=None: fake_cm()):
        yield


def make_agent_event(path_suffix: str, method: str, body: dict, claims: dict | None = None):
    """Build API Gateway event for POST /agent (direct route)."""
    path = f"/dev/{path_suffix.lstrip('/')}"
    claims = claims or {"custom:role": "doctor", "sub": "test-doc", "email": "doc@test"}
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": None,
        "requestContext": {"path": path, "authorizer": {"claims": claims}},
        "body": json.dumps(body),
        "queryStringParameters": None,
    }


def post_agent_via_handler(body: dict) -> tuple[int, dict]:
    """Invoke router handler directly (no HTTP)."""
    event = make_agent_event("agent", "POST", body)
    with _mock_get_session():
        from cdss.api.handlers.router import handler
        resp = handler(event, None)
    status = int(resp.get("statusCode", 500))
    raw_body = resp.get("body", "{}")
    data = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    return status, data


def post_agent_via_http(body: dict) -> tuple[int, dict]:
    """POST /agent via HTTP (when BASE_URL is set)."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL.rstrip('/')}/agent",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as f:
            return f.status, json.loads(f.read().decode("utf-8"))
    except Exception as e:
        return 0, {"error": str(e)}


def post_agent(body: dict) -> tuple[int, dict]:
    global _http_unavailable
    if USE_HTTP and _http_unavailable:
        return post_agent_via_handler(body)
    if USE_HTTP:
        status, data = post_agent_via_http(body)
        err = str(data.get("error", "")).lower()
        if status == 0 and ("refused" in err or "connection" in err or "10061" in err):
            _http_unavailable = True
            return post_agent_via_handler(body)
        return status, data
    return post_agent_via_handler(body)


INTENT_SCENARIOS = [
    ("patient", "Give me a summary of patient history for PT-1001"),
    ("surgery", "What is the surgery checklist for the next operation?"),
    ("resource", "Check OT and equipment availability"),
    ("scheduling", "Show the schedule and book a slot"),
    ("engagement", "Send medication reminder to the patient"),
]


def assert_agent_envelope(data: dict, require_correlation_id: bool = True) -> None:
    """Validate response envelope: intent, agent, data, safety_disclaimer, optional correlationId."""
    assert isinstance(data, dict), "Response must be a JSON object"
    assert "intent" in data, "Missing intent"
    assert "agent" in data, "Missing agent"
    assert "data" in data, "Missing data"
    assert "safety_disclaimer" in data, "Missing safety_disclaimer"
    if require_correlation_id:
        assert "correlationId" in data, "Missing correlationId"
    assert isinstance(data["safety_disclaimer"], str), "safety_disclaimer must be string"
    assert len(data["safety_disclaimer"]) > 0, "safety_disclaimer must be non-empty"


def test_intent_scenarios(run_ctx) -> tuple[int, int]:
    passed = 0
    failed = 0
    with run_ctx:
        for expected_intent, message in INTENT_SCENARIOS:
            status, data = post_agent({"message": message})
            if status != 200:
                print(f"  FAIL intent={expected_intent}: status={status} body={data}")
                failed += 1
                continue
            try:
                assert_agent_envelope(data)
                intent = data.get("intent", "")
                passed += 1
                print(f"  OK   intent={intent} (scenario {expected_intent})")
            except AssertionError as e:
                print(f"  FAIL intent={expected_intent}: {e}")
                failed += 1
    return passed, failed


def test_fallback_when_bedrock_unavailable() -> tuple[int, int]:
    passed = 0
    failed = 0
    with patch.dict(os.environ, {"BEDROCK_CONFIG_SECRET_NAME": ""}, clear=False):
        with _mock_get_session():
            status, data = post_agent({"message": "patient summary for PT-101"})
    if status != 200:
        print("  FAIL fallback: non-200 status", status, data)
        failed += 1
        return passed, failed
    try:
        assert_agent_envelope(data)
        assert data.get("intent") in (
            "patient", "general", "surgery", "resource", "scheduling", "engagement", "hospitals", "triage"
        )
        passed += 1
        print("  OK   fallback: envelope valid, intent from keyword fallback")
    except AssertionError as e:
        print("  FAIL fallback:", e)
        failed += 1
    return passed, failed


def test_message_required() -> tuple[int, int]:
    run_ctx = nullcontext() if USE_HTTP else _mock_get_session()
    with run_ctx:
        status, data = post_agent({"message": ""})
    if status == 400 and isinstance(data.get("error"), str):
        print("  OK   message required: 400 with error")
        return 1, 0
    if status == 200 and isinstance(data.get("data"), dict):
        print("  OK   message required: handled (200)")
        return 1, 0
    print("  FAIL message required: expected 400 or handled 200", status, data)
    return 0, 1


def main() -> int:
    global _http_unavailable
    use_db = bool(os.environ.get("DATABASE_URL") or os.environ.get("RDS_CONFIG_SECRET_NAME"))
    run_ctx = nullcontext() if use_db else _mock_get_session()

    # If BASE_URL is set but server is not reachable, use handler for entire run
    if USE_HTTP:
        _, data = post_agent_via_http({"message": "probe"})
        err = str(data.get("error", "")).lower()
        if err and ("refused" in err or "connection" in err or "10061" in err):
            _http_unavailable = True

    print("Agent REST tests (POST /agent)")
    print("  BASE_URL=%s (HTTP=%s)" % (BASE_URL or "none", USE_HTTP and not _http_unavailable))
    if _http_unavailable:
        print("  (Server not reachable; using direct handler.)")
    print("  DB=%s" % ("real" if use_db else "mocked"))
    print("-" * 50)

    total_pass = 0
    total_fail = 0

    p, f = test_intent_scenarios(run_ctx)
    total_pass += p
    total_fail += f

    if not USE_HTTP or _http_unavailable:
        p, f = test_fallback_when_bedrock_unavailable()
        total_pass += p
        total_fail += f

    p, f = test_message_required()
    total_pass += p
    total_fail += f

    print("-" * 50)
    print("Total: passed=%d failed=%d" % (total_pass, total_fail))
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
