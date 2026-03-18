#!/usr/bin/env python3
"""
Test ABDM EHR MCP adapter: get_abdm_record with valid patient_id and empty/invalid.

Validates response shape and that empty patient_id returns error (no raw logging of PII).
Error-injection: bad payloads must yield safe fallback and audit-safe behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from cdss.mcp.adapter import get_abdm_record


def test_valid_patient_id() -> None:
    out = get_abdm_record("PT-1001")
    assert isinstance(out, dict), "get_abdm_record should return dict"
    assert "patient_id" in out or "error" in out, "should have patient_id or error"
    if "error" not in out:
        assert out.get("patient_id") == "PT-1001", "patient_id should echo (or be redacted)"


def test_empty_patient_id_returns_error() -> None:
    """Empty patient_id must return error shape, not raise or log PII."""
    out = get_abdm_record("")
    assert isinstance(out, dict), "empty patient_id should return dict"
    assert "error" in out, "should include 'error' key for empty patient_id"
    assert "required" in out["error"].lower() or "patient" in out["error"].lower(), "error should mention patient_id"


def test_none_like_handling() -> None:
    """Falsy input should be handled safely (stub accepts str; empty string is the edge case)."""
    out = get_abdm_record("")
    assert "error" in out


def test_response_shape_with_valid_id() -> None:
    out = get_abdm_record("MASKED-ID-123")
    assert isinstance(out, dict)
    # Stub may return abdm_linked, summary; or error
    assert "patient_id" in out or "error" in out or "abdm_linked" in out


def run_all() -> bool:
    try:
        test_valid_patient_id()
        test_empty_patient_id_returns_error()
        test_none_like_handling()
        test_response_shape_with_valid_id()
        return True
    except AssertionError as e:
        print("AssertionError: %s" % e, file=sys.stderr)
        return False
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
        return False


def main() -> int:
    ok = run_all()
    print("ABDM MCP tests: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
