#!/usr/bin/env python3
"""
Verify CDSS models (Bedrock) and test all API endpoints.

Usage (from repo root):
  # Load .env then run (default: base URL http://localhost:8080)
  python scripts/verify_models_and_endpoints.py

  # Custom base URL (e.g. deployed API)
  python scripts/verify_models_and_endpoints.py --base-url https://your-api.execute-api.ap-south-1.amazonaws.com/dev

  # Skip Bedrock invoke (only check config load)
  python scripts/verify_models_and_endpoints.py --skip-bedrock-invoke

  # Skip endpoint tests (only verify models)
  python scripts/verify_models_and_endpoints.py --skip-endpoints

Start the local API first: python scripts/run_api_local.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
except ImportError:
    pass


# ---------- Model verification ----------

def verify_bedrock_config(skip_invoke: bool) -> dict:
    """Check Bedrock config (env + Secrets Manager) and optionally test invoke."""
    out = {
        "configured": False,
        "source": None,
        "model_id": None,
        "region": None,
        "secret_loaded": False,
        "invoke_ok": None,
        "error": None,
    }
    secret_name = (os.environ.get("BEDROCK_CONFIG_SECRET_NAME") or "").strip()
    model_id_env = (os.environ.get("BEDROCK_MODEL_ID") or "").strip()

    if secret_name:
        out["source"] = "BEDROCK_CONFIG_SECRET_NAME"
        try:
            from cdss.config.secrets import get_bedrock_config
            cfg = get_bedrock_config()
            if cfg:
                out["configured"] = True
                out["model_id"] = (cfg.get("model_id") or "apac.amazon.nova-lite-v1:0").strip()
                out["region"] = (cfg.get("region") or os.environ.get("AWS_REGION") or "ap-south-1").strip()
                out["secret_loaded"] = True
            else:
                out["error"] = "Secret returned empty or not found"
        except Exception as e:
            out["error"] = str(e)
    elif model_id_env:
        out["source"] = "BEDROCK_MODEL_ID (env)"
        out["configured"] = True
        out["model_id"] = model_id_env
        out["region"] = (os.environ.get("AWS_REGION") or "ap-south-1").strip()
        out["secret_loaded"] = False  # no secret
    else:
        out["error"] = "Neither BEDROCK_CONFIG_SECRET_NAME nor BEDROCK_MODEL_ID set"

    if not out["configured"] or skip_invoke:
        return out

    # Optional: test Bedrock invoke (Converse)
    try:
        from cdss.bedrock.chat import invoke_chat
        result = invoke_chat("Reply with exactly: OK")
        out["invoke_ok"] = bool(result.reply and "OK" in result.reply)
        if not out["invoke_ok"]:
            out["invoke_error"] = result.message or result.reply[:200]
    except Exception as e:
        out["invoke_ok"] = False
        out["invoke_error"] = str(e)

    return out


def run_model_verification(skip_invoke: bool) -> bool:
    """Print model status and return True if models are verified/working."""
    print("\n" + "=" * 60)
    print("  MODEL VERIFICATION (Bedrock)")
    print("=" * 60)

    bedrock = verify_bedrock_config(skip_invoke)

    if bedrock.get("error"):
        print("  Status: NOT CONFIGURED")
        print(f"  Reason: {bedrock['error']}")
        print("  Set BEDROCK_CONFIG_SECRET_NAME or BEDROCK_MODEL_ID in .env for AI features.")
        return False

    print("  Status: CONFIGURED")
    print(f"  Source: {bedrock.get('source', 'N/A')}")
    print(f"  Model:  {bedrock.get('model_id', 'N/A')}")
    print(f"  Region: {bedrock.get('region', 'N/A')}")
    if bedrock.get("secret_loaded"):
        print("  Secret: loaded from Secrets Manager")
    if skip_invoke:
        print("  Invoke: skipped (use without --skip-bedrock-invoke to test)")
    elif bedrock.get("invoke_ok") is not None:
        if bedrock["invoke_ok"]:
            print("  Invoke: OK (Bedrock responded)")
        else:
            print("  Invoke: FAILED")
            print(f"  Detail: {bedrock.get('invoke_error', 'Unknown')}")
            return False

    print("=" * 60)
    return True


# ---------- Endpoint tests ----------

def make_request(base_url: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """Return (status_code, response_body)."""
    import urllib.request
    import urllib.error

    url = (base_url.rstrip("/") + path) if path.startswith("/") else (base_url + "/" + path)
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-CDSS-Role", "doctor")
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            raw = res.read().decode("utf-8")
            try:
                return res.status, json.loads(raw)
            except json.JSONDecodeError:
                return res.status, {"raw": raw[:500]}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw[:300]}
    except OSError as e:
        return 0, {"error": str(e)}


def run_endpoint_tests(base_url: str) -> dict[str, str]:
    """Test all documented endpoints; return dict of endpoint -> PASS/FAIL/SKIP."""
    results = {}

    # Health & core
    status, _ = make_request(base_url, "GET", "/health")
    results["GET /health"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/dashboard")
    results["GET /dashboard"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, body = make_request(base_url, "POST", "/agent", {"message": "Hello"})
    results["POST /agent"] = "PASS" if status == 200 and (body.get("reply") or body.get("message")) else f"FAIL ({status})"

    # Patients
    status, _ = make_request(base_url, "GET", "/api/v1/patients")
    results["GET /api/v1/patients"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/patients/PT-1001")
    results["GET /api/v1/patients/{id}"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Surgeries
    status, _ = make_request(base_url, "GET", "/api/v1/surgeries")
    results["GET /api/v1/surgeries"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/surgeries/SRG-001")
    results["GET /api/v1/surgeries/{id}"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Medications, resources, schedule
    status, _ = make_request(base_url, "GET", "/api/v1/medications")
    results["GET /api/v1/medications"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/resources")
    results["GET /api/v1/resources"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/schedule")
    results["GET /api/v1/schedule"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Consultations
    status, body = make_request(base_url, "POST", "/api/v1/consultations/start", {"patient_id": "PT-1001", "doctor_id": "DOC-001"})
    results["POST /api/v1/consultations/start"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/v1/consultations", {"patient_id": "PT-1001", "notes": "Test"})
    results["POST /api/v1/consultations"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Appointments & tasks
    status, _ = make_request(base_url, "GET", "/api/v1/appointments")
    results["GET /api/v1/appointments"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/tasks")
    results["GET /api/v1/tasks"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Terminology
    status, _ = make_request(base_url, "GET", "/api/v1/terminology")
    results["GET /api/v1/terminology"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Activity
    status, _ = make_request(base_url, "POST", "/api/v1/activity", {"action": "view", "resource": "patient", "resource_id": "PT-1001"})
    results["POST /api/v1/activity"] = "PASS" if status in (200, 201, 204) else f"FAIL ({status})"

    # AI endpoints
    status, _ = make_request(base_url, "POST", "/api/v1/ai/summarize", {"text": "Patient has hypertension."})
    results["POST /api/v1/ai/summarize"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/ai/summarize", {"text": "Patient has hypertension."})
    results["POST /api/ai/summarize"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/v1/ai/entities", {"text": "Patient on Metformin 500mg."})
    results["POST /api/v1/ai/entities"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/ai/prescription", {"patient_id": "PT-1001", "conditions": ["Hypertension"]})
    results["POST /api/ai/prescription"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/ai/adherence", {"patient_id": "PT-1001"})
    results["POST /api/ai/adherence"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/ai/engagement", {"patient_id": "PT-1001"})
    results["POST /api/ai/engagement"] = "PASS" if status == 200 else f"FAIL ({status})"

    status, _ = make_request(base_url, "POST", "/api/ai/resources", {"diagnosis": "Hypertension"})
    results["POST /api/ai/resources"] = "PASS" if status == 200 else f"FAIL ({status})"

    # Admin (expect 403 when role=doctor)
    status, _ = make_request(base_url, "GET", "/api/v1/admin/users")
    results["GET /api/v1/admin/users"] = "PASS" if status in (200, 403) else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/admin/audit")
    results["GET /api/v1/admin/audit"] = "PASS" if status in (200, 403) else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/admin/config")
    results["GET /api/v1/admin/config"] = "PASS" if status in (200, 403) else f"FAIL ({status})"

    status, _ = make_request(base_url, "GET", "/api/v1/admin/analytics")
    results["GET /api/v1/admin/analytics"] = "PASS" if status in (200, 403) else f"FAIL ({status})"

    # Docs
    status, _ = make_request(base_url, "GET", "/docs/swagger.yaml")
    results["GET /docs/swagger.yaml"] = "PASS" if status == 200 else f"FAIL ({status})"

    return results


def main():
    parser = argparse.ArgumentParser(description="Verify CDSS models and test all endpoints")
    parser.add_argument("--base-url", default="http://localhost:8080", help="API base URL")
    parser.add_argument("--skip-bedrock-invoke", action="store_true", help="Do not call Bedrock (only check config)")
    parser.add_argument("--skip-endpoints", action="store_true", help="Only run model verification")
    parser.add_argument("--skip-models", action="store_true", help="Only run endpoint tests")
    args = parser.parse_args()

    models_ok = True
    if not args.skip_models:
        models_ok = run_model_verification(args.skip_bedrock_invoke)

    if not args.skip_endpoints:
        print("\n" + "=" * 60)
        print("  ENDPOINT TESTS")
        print("  Base URL:", args.base_url)
        print("=" * 60)
        results = run_endpoint_tests(args.base_url)
        for name, result in results.items():
            icon = "PASS" if result == "PASS" else "FAIL"
            sym = "[PASS]" if result == "PASS" else "[FAIL]"
            print(f"  {sym}  {name}")
        print("=" * 60)
        passed = sum(1 for r in results.values() if r == "PASS")
        total = len(results)
        print(f"  Result: {passed}/{total} endpoints passed")
        print("=" * 60)
        if passed < total:
            sys.exit(2)

    if not models_ok:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
