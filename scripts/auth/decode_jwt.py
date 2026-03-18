#!/usr/bin/env python3
"""
Decode a Cognito JWT and print claims; verify presence of custom:role (or role).

Does not verify signature (API Gateway does that). Use for inspecting test tokens
and ensuring custom:role is set for RBAC.

Usage:
  # From argument
  python scripts/auth/decode_jwt.py 'eyJraWQ...'

  # From stdin (e.g. pipe from get_token.py)
  python scripts/auth/get_token.py -u user -p pass | python scripts/auth/decode_jwt.py -

  # Exit 1 if custom:role missing
  python scripts/auth/decode_jwt.py -q --require-role 'eyJ...'
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def decode_jwt_payload(token: str) -> dict:
    """
    Decode JWT payload (middle segment) without signature verification.

    :param token: Raw JWT string
    :return: Payload dict (claims)
    :raises: ValueError if token format is invalid
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("JWT must have three segments")
    payload_b64 = parts[1]
    # Add padding if needed
    pad = 4 - len(payload_b64) % 4
    if pad != 4:
        payload_b64 += "=" * pad
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 payload: {e}") from e
    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid JSON payload: {e}") from e


def get_role(claims: dict) -> str:
    """Return role from custom:role or role claim (normalized lower)."""
    role = (
        (claims.get("custom:role") or claims.get("role") or "")
        .strip()
        .strip("'\"")
        .lower()
    )
    return role


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decode Cognito JWT and print claims; optionally require custom:role."
    )
    parser.add_argument(
        "token",
        nargs="?",
        default=None,
        help="JWT string, or '-' to read from stdin",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print role and exit code (no claim dump)",
    )
    parser.add_argument(
        "--require-role",
        action="store_true",
        help="Exit 1 if custom:role (or role) is missing or empty",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw payload as single-line JSON",
    )
    args = parser.parse_args()

    token = args.token
    if token == "-" or token is None:
        token = sys.stdin.read().strip()
    if not token:
        print("Error: No token provided.", file=sys.stderr)
        return 1

    try:
        claims = decode_jwt_payload(token)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    role = get_role(claims)
    if args.require_role and not role:
        if not args.quiet:
            print("Error: JWT has no custom:role (or role) claim.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(claims))
        return 0

    if args.quiet:
        print(role)
        return 0

    # Pretty-print important claims
    print("Claims (payload):")
    print("-" * 40)
    for key in sorted(claims.keys()):
        val = claims[key]
        if key == "role" or key == "custom:role":
            print(f"  {key}: {val!r}  <- RBAC role")
        else:
            print(f"  {key}: {val!r}")
    print("-" * 40)
    print(f"Resolved role: {role!r}")
    if not role and not args.require_role:
        print("Warning: No custom:role/role claim. API may treat as anonymous.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
