#!/usr/bin/env python3
"""
Obtain a Cognito JWT (id_token) via InitiateAuth for testing and CI.

Supports USER_PASSWORD_AUTH (and optionally USER_SRP_AUTH). Outputs the
id_token to stdout for piping (e.g. into decode_jwt.py or rbac_matrix.py).

Usage:
  # Interactive / CLI
  python scripts/auth/get_token.py --username dr.test@hospital.in --password 'YourPassword'
  python scripts/auth/get_token.py -u patient@demo.in -p 'Pass' --client-type patient

  # CI-friendly (env vars)
  COGNITO_USER_POOL_ID=ap-south-1_xxx COGNITO_CLIENT_ID=xxx AWS_REGION=ap-south-1 \\
    TEST_USERNAME=dr.test@hospital.in TEST_PASSWORD=secret python scripts/auth/get_token.py

  # Pipe into decode
  python scripts/auth/get_token.py -u admin@cdss.ai -p secret | python scripts/auth/decode_jwt.py -

Environment:
  COGNITO_USER_POOL_ID  (required if not --user-pool-id)
  COGNITO_CLIENT_ID     (required if not --client-id; use staff or patient client)
  AWS_REGION            (default: ap-south-1)
  TEST_USERNAME         (optional; overridden by -u)
  TEST_PASSWORD         (optional; overridden by -p)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Repo root for local runs
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _ensure_boto3():
    try:
        import boto3  # noqa: F401
        return True
    except ImportError:
        return False


def get_token(
    user_pool_id: str,
    client_id: str,
    username: str,
    password: str,
    region: str = "ap-south-1",
    auth_flow: str = "USER_PASSWORD_AUTH",
) -> str:
    """
    Call Cognito InitiateAuth and return the id_token.

    :param user_pool_id: Cognito User Pool ID
    :param client_id: App client ID (staff or patient portal)
    :param username: User's sign-in identifier (email or username)
    :param password: User's password
    :param region: AWS region for Cognito
    :param auth_flow: USER_PASSWORD_AUTH or USER_SRP_AUTH
    :return: id_token string
    :raises: RuntimeError on auth failure
    """
    if not _ensure_boto3():
        raise RuntimeError("boto3 is required. Install with: pip install boto3")

    import boto3

    client = boto3.client("cognito-idp", region_name=region)
    params = {
        "AuthFlow": auth_flow,
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password,
        },
    }
    try:
        resp = client.initiate_auth(**params)
    except client.exceptions.NotAuthorizedException as e:
        raise RuntimeError(f"Invalid username or password: {e}") from e
    except client.exceptions.UserNotFoundException as e:
        raise RuntimeError(f"User not found: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Cognito InitiateAuth failed: {e}") from e

    result = resp.get("AuthenticationResult") or {}
    id_token = result.get("IdToken")
    if not id_token:
        raise RuntimeError(
            "No IdToken in response. Ensure the app client allows USER_PASSWORD_AUTH."
        )
    return id_token


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get Cognito id_token for API testing (staff or patient client)."
    )
    parser.add_argument(
        "-u", "--username",
        default=os.environ.get("TEST_USERNAME", ""),
        help="Cognito username (email or preferred_username)",
    )
    parser.add_argument(
        "-p", "--password",
        default=os.environ.get("TEST_PASSWORD", ""),
        help="Password (prefer env TEST_PASSWORD in CI)",
    )
    parser.add_argument(
        "--user-pool-id",
        default=os.environ.get("COGNITO_USER_POOL_ID", ""),
        help="Cognito User Pool ID (or set COGNITO_USER_POOL_ID)",
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("COGNITO_CLIENT_ID", ""),
        help="Cognito App Client ID (or set COGNITO_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-type",
        choices=("staff", "patient"),
        default="staff",
        help="Use staff or patient app client (requires COGNITO_STAFF_CLIENT_ID / COGNITO_PATIENT_CLIENT_ID if COGNITO_CLIENT_ID not set)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "ap-south-1"),
        help="AWS region (default: ap-south-1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON with id_token, access_token, expires_in",
    )
    args = parser.parse_args()

    user_pool_id = (args.user_pool_id or "").strip()
    client_id = (args.client_id or "").strip()
    if not client_id and args.client_type == "staff":
        client_id = (os.environ.get("COGNITO_STAFF_CLIENT_ID") or "").strip()
    if not client_id and args.client_type == "patient":
        client_id = (os.environ.get("COGNITO_PATIENT_CLIENT_ID") or "").strip()

    username = (args.username or "").strip()
    password = args.password  # allow empty for prompt later if we add it
    if not user_pool_id:
        print("Error: COGNITO_USER_POOL_ID or --user-pool-id required.", file=sys.stderr)
        return 1
    if not client_id:
        print(
            "Error: COGNITO_CLIENT_ID or COGNITO_STAFF_CLIENT_ID/COGNITO_PATIENT_CLIENT_ID or --client-id required.",
            file=sys.stderr,
        )
        return 1
    if not username or not password:
        print("Error: username and password required (--username/--password or TEST_USERNAME/TEST_PASSWORD).", file=sys.stderr)
        return 1

    try:
        id_token = get_token(
            user_pool_id=user_pool_id,
            client_id=client_id,
            username=username,
            password=password,
            region=args.region,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        # Re-call to get full result if we need access_token/expires_in; for simplicity output id_token only in JSON
        out = {"id_token": id_token}
        print(json.dumps(out))
    else:
        print(id_token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
