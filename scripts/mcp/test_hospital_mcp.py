#!/usr/bin/env python3
"""
Test Hospital Systems MCP adapter: get_hospital_data for ot_status, beds, equipment.

Validates response shape and expected fields. Run offline (adapter is stubbed).
Error-injection: pass invalid data_type to assert safe fallback and error shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from cdss.mcp.adapter import get_hospital_data


def test_ot_status() -> None:
    out = get_hospital_data("ot_status")
    assert isinstance(out, dict), "ot_status should return dict"
    assert "ots" in out, "ot_status should have 'ots' key"
    assert isinstance(out["ots"], list), "'ots' should be list"
    for ot in out["ots"]:
        assert "id" in ot and "status" in ot, "Each OT should have id and status"


def test_beds() -> None:
    out = get_hospital_data("beds")
    assert isinstance(out, dict), "beds should return dict"
    assert "beds" in out, "beds should have 'beds' key"
    assert isinstance(out["beds"], list), "'beds' should be list"
    for b in out["beds"]:
        assert "id" in b and "status" in b, "Each bed should have id and status"


def test_equipment() -> None:
    out = get_hospital_data("equipment")
    assert isinstance(out, dict), "equipment should return dict"
    assert "equipment" in out, "equipment should have 'equipment' key"
    assert isinstance(out["equipment"], list), "'equipment' should be list"


def test_unknown_type_returns_error_shape() -> None:
    """Error-injection: unknown data_type must return safe error shape, not raise."""
    out = get_hospital_data("unknown_type_xyz")
    assert isinstance(out, dict), "unknown type should return dict (safe fallback)"
    assert "error" in out, "should include 'error' key"
    assert "unknown" in out["error"].lower() or "unknown_type" in out["error"].lower(), "error message should mention unknown type"


def test_empty_data_type_returns_error_shape() -> None:
    """Invalid input: empty or invalid data_type should not crash."""
    out = get_hospital_data("")
    assert isinstance(out, dict), "empty type should return dict"
    assert "error" in out, "should include 'error' key"


def run_all() -> bool:
    try:
        test_ot_status()
        test_beds()
        test_equipment()
        test_unknown_type_returns_error_shape()
        test_empty_data_type_returns_error_shape()
        return True
    except AssertionError as e:
        print("AssertionError: %s" % e, file=sys.stderr)
        return False
    except Exception as e:
        print("Error: %s" % e, file=sys.stderr)
        return False


def main() -> int:
    ok = run_all()
    print("Hospital MCP tests: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
