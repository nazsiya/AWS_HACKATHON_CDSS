#!/usr/bin/env python3
"""
RBAC matrix tester: run key API endpoints with a single token and assert
role-based expectations (200, 403, 404).

Decodes the JWT to determine role (doctor, nurse, admin, superuser, patient), then
runs a preset list of (method, path, expected_status) for that role.
For patient role, PATIENT_ID is used where the path contains a patient id.

Usage:
  # Single token (role inferred from JWT)
  python scripts/api_test_utils/rbac_matrix.py --base-url https://xxx.execute-api.ap-south-1.amazonaws.com/dev --token "eyJ..."
  python scripts/api_test_utils/rbac_matrix.py --base-url https://xxx/dev --token "$(python scripts/auth/get_token.py -u doc@test.in -p secret)" --patient-id PT-1001

  # Env-based (CI-friendly)
  BASE_URL=https://xxx/dev TOKEN=$(python scripts/auth/get_token.py ...) python scripts/api_test_utils/rbac_matrix.py
  BASE_URL=... TOKEN=... PATIENT_ID=PT-1001 python scripts/api_test_utils/rbac_matrix.py

  # Verbose / quiet
  python scripts/api_test_utils/rbac_matrix.py --base-url ... --token ... -v
  python scripts/api_test_utils/rbac_matrix.py --base-url ... --token ... -q
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add repo root for loading decode_jwt without package layout
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT_AUTH = _REPO_ROOT / "scripts" / "auth"


def _load_decode_jwt():
    """Load decode_jwt_payload and get_role from scripts/auth/decode_jwt.py."""
    import importlib.util
    path = _SCRIPT_AUTH / "decode_jwt.py"
    if not path.exists():
        return None, None
    spec = importlib.util.spec_from_file_location("decode_jwt", path)
    if spec is None or spec.loader is None:
        return None, None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "decode_jwt_payload", None), getattr(mod, "get_role", None)


def _decode_jwt_fallback(token: str) -> dict:
    import base64
    parts = token.strip().split(".")
    if len(parts) != 3:
        return {}
    payload_b64 = parts[1]
    pad = 4 - len(payload_b64) % 4
    if pad != 4:
        payload_b64 += "=" * pad
    try:
        return json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
    except Exception:
        return {}


def _get_role_fallback(claims: dict) -> str:
    return (
        (claims.get("custom:role") or claims.get("role") or "")
        .strip()
        .strip("'\"")
        .lower()
    )


_decode_jwt_payload, _get_role = _load_decode_jwt()
if _decode_jwt_payload is None:
    _decode_jwt_payload = _decode_jwt_fallback
    _get_role = _get_role_fallback
decode_jwt_payload = _decode_jwt_payload
get_role = _get_role


# Role presets: list of (method, path_suffix, expected_status_codes)
# path_suffix is relative to base_url; {patient_id} is replaced by PATIENT_ID.
STAFF_OK = [200, 201, 204]
STAFF_OR_404 = [200, 201, 204, 404]
ADMIN_ONLY = [403]  # staff should get 403
PATIENT_FORBIDDEN = [403]
PATIENT_OWN_OK = [200, 404]  # own record may be 200 or 404

ROLE_MATRIX: dict[str, list[tuple[str, str, list[int]]]] = {
    "admin": [
        ("GET", "/dashboard", STAFF_OK),
        ("GET", "/api/v1/patients", STAFF_OK),
        ("GET", "/api/v1/patients/PT-1001", STAFF_OR_404),
        ("GET", "/api/v1/surgeries", STAFF_OK),
        ("GET", "/api/v1/resources", STAFF_OK),
        ("GET", "/api/v1/schedule", STAFF_OK),
        ("GET", "/api/v1/admin/audit", STAFF_OK),
        ("GET", "/api/v1/admin/users", STAFF_OR_404),
        ("GET", "/api/v1/admin/config", STAFF_OR_404),
        ("POST", "/agent", STAFF_OK),
    ],
    "superuser": [
        ("GET", "/dashboard", STAFF_OK),
        ("GET", "/api/v1/patients", STAFF_OK),
        ("GET", "/api/v1/patients/PT-1001", STAFF_OR_404),
        ("GET", "/api/v1/surgeries", STAFF_OK),
        ("GET", "/api/v1/resources", STAFF_OK),
        ("GET", "/api/v1/schedule", STAFF_OK),
        ("GET", "/api/v1/admin/audit", STAFF_OK),
        ("GET", "/api/v1/admin/users", STAFF_OR_404),
        ("GET", "/api/v1/admin/config", STAFF_OR_404),
        ("POST", "/agent", STAFF_OK),
    ],
    "doctor": [
        ("GET", "/dashboard", STAFF_OK),
        ("GET", "/api/v1/patients", STAFF_OK),
        ("GET", "/api/v1/patients/PT-1001", STAFF_OR_404),
        ("GET", "/api/v1/surgeries", STAFF_OK),
        ("GET", "/api/v1/resources", STAFF_OK),
        ("GET", "/api/v1/schedule", STAFF_OK),
        ("GET", "/api/v1/admin/audit", ADMIN_ONLY),
        ("GET", "/api/v1/admin/users", ADMIN_ONLY),
        ("POST", "/agent", STAFF_OK),
    ],
    "nurse": [
        ("GET", "/dashboard", STAFF_OK),
        ("GET", "/api/v1/patients", STAFF_OK),
        ("GET", "/api/v1/patients/PT-1001", STAFF_OR_404),
        ("GET", "/api/v1/surgeries", STAFF_OK),
        ("GET", "/api/v1/resources", STAFF_OK),
        ("GET", "/api/v1/schedule", STAFF_OK),
        ("GET", "/api/v1/admin/audit", ADMIN_ONLY),
        ("POST", "/agent", STAFF_OK),
    ],
    "patient": [
        ("GET", "/dashboard", [200]),
        ("GET", "/api/v1/patients", PATIENT_FORBIDDEN),
        ("GET", "/api/v1/patients/{patient_id}", PATIENT_OWN_OK),
        ("GET", "/api/v1/surgeries", [200]),
        ("GET", "/api/v1/admin/audit", PATIENT_FORBIDDEN),
        ("POST", "/agent", [200]),
    ],
}

# Fallback for unknown role: treat as staff (doctor) for non-admin paths
DEFAULT_MATRIX = ROLE_MATRIX["doctor"]


def _request(
    base_url: str,
    method: str,
    path: str,
    token: str,
    timeout: int = 15,
) -> tuple[int, str]:
    """Perform HTTP request; return (status_code, body_preview)."""
    try:
        import urllib.request
    except ImportError:
        try:
            import urllib.request as urllib_request
        except ImportError:
            return -1, "urllib not available"
    url = (base_url.rstrip("/") + path).replace("//", "/")
    if url.startswith("https:/") and not url.startswith("https://"):
        url = "https://" + url[7:]
    elif url.startswith("http:/") and not url.startswith("http://"):
        url = "http://" + url[6:]
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    if method in ("POST", "PUT", "PATCH"):
        req.data = b"{}"
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:500]
            return resp.status, body
    except Exception as e:
        err = str(e)
        if hasattr(e, "code"):
            return getattr(e, "code", -1), err
        if "401" in err or "Unauthorized" in err:
            return 401, err
        if "403" in err or "Forbidden" in err:
            return 403, err
        return -1, err


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run RBAC matrix against deployed API with one token (role from JWT)."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", ""),
        help="API base URL (e.g. https://xxx.execute-api.ap-south-1.amazonaws.com/dev)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("TOKEN", ""),
        help="Cognito id_token (or set TOKEN)",
    )
    parser.add_argument(
        "--patient-id",
        default=os.environ.get("PATIENT_ID", "PT-1001"),
        help="Patient ID for patient-role own-record path (default: PT-1001)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each request and response",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print summary (pass/fail count)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Request timeout in seconds (default: 15)",
    )
    args = parser.parse_args()

    base_url = (args.base_url or "").strip().rstrip("/")
    token = (args.token or "").strip()
    patient_id = (args.patient_id or "PT-1001").strip()

    if not base_url:
        print("Error: --base-url or BASE_URL required.", file=sys.stderr)
        return 1
    if not token:
        print("Error: --token or TOKEN required.", file=sys.stderr)
        return 1

    claims = decode_jwt_payload(token)
    role = get_role(claims)
    if not role:
        print("Warning: JWT has no custom:role; using 'doctor' matrix.", file=sys.stderr)
        role = "doctor"

    matrix = ROLE_MATRIX.get(role) or DEFAULT_MATRIX
    if not args.quiet:
        print(f"Role: {role!r} | Base URL: {base_url} | Patient ID: {patient_id}")
        print("-" * 60)

    passed = 0
    failed = 0
    for method, path_suffix, allowed in matrix:
        path = path_suffix.replace("{patient_id}", patient_id)
        status, body = _request(base_url, method, path, token, timeout=args.timeout)
        ok = status in allowed
        if ok:
            passed += 1
        else:
            failed += 1
        if args.verbose or not ok:
            print(f"  [{method:4}] {path} -> {status} (allowed: {allowed}) {'OK' if ok else 'FAIL'}")
            if (args.verbose or not ok) and body:
                preview = body.replace("\n", " ")[:120]
                print(f"           {preview}")
    if not args.quiet:
        print("-" * 60)
        print(f"Passed: {passed}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
