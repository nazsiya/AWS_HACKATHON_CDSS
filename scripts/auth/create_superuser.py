#!/usr/bin/env python3
"""
Create or update a Cognito user with the superuser role (full access).

No console required: uses boto3 to create the user and set custom:role=superuser.
User Pool ID can come from env, Terraform output, or Secrets Manager app-config.

Usage:
  # From repo root (picks up Terraform output if run from infrastructure/)
  python scripts/auth/create_superuser.py --email superuser@cdss.ai --password 'YourSecurePassword'

  # Create demo user for deployed dashboard (demo@cdss.ai; set DEMO_PASSWORD in env)
  python scripts/auth/create_superuser.py --demo

  # With explicit User Pool ID
  COGNITO_USER_POOL_ID=ap-south-1_xxxxxxxxx python scripts/auth/create_superuser.py \\
    --email superuser@cdss.ai --password 'YourSecurePassword'

  # Update existing user to superuser (keeps current password if you omit --password)
  python scripts/auth/create_superuser.py --email admin@cdss.ai --set-role-only

Environment:
  COGNITO_USER_POOL_ID  Optional; can also get from Terraform (cd infrastructure && terraform output -raw cognito_user_pool_id)
  AWS_REGION            Default ap-south-1
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _get_user_pool_id_from_terraform() -> str | None:
    """Try to get cognito_user_pool_id from Terraform output."""
    infra = _REPO_ROOT / "infrastructure"
    if not (infra / "terraform.tfstate").exists() and not (infra / ".terraform").exists():
        return None
    try:
        out = subprocess.run(
            ["terraform", "output", "-raw", "cognito_user_pool_id"],
            cwd=infra,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_user_pool_id_from_secrets() -> str | None:
    """Try to get cognito_user_pool_id from CDSS app config secret."""
    try:
        import boto3
        secret_name = os.environ.get("CDSS_APP_CONFIG_SECRET_NAME", "cdss-dev/app-config")
        region = os.environ.get("AWS_REGION", "ap-south-1")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        import json
        data = json.loads(resp.get("SecretString", "{}"))
        return (data.get("cognito_user_pool_id") or "").strip() or None
    except Exception:
        return None


def _pool_uses_email_alias(client, user_pool_id: str) -> bool:
    """Return True if the user pool uses email as an alias (Username must not be email format)."""
    try:
        resp = client.describe_user_pool(UserPoolId=user_pool_id)
        pool = resp.get("UserPool", {})
        # Email as alias: AliasAttributes or UsernameAttributes (primary username)
        aliases = pool.get("AliasAttributes") or []
        attrs = pool.get("UsernameAttributes") or []
        return "email" in aliases or "email" in attrs
    except Exception:
        return False


def _username_slug(email: str) -> str:
    """Return a stable non-email username for pools that use email alias."""
    return email.strip().lower().replace("@", "_at_").replace(".", "_")


def _find_username_by_email(client, user_pool_id: str, email: str) -> str | None:
    """Find Cognito Username for a user with the given email attribute (for email-alias pools)."""
    want = email.strip().lower()
    pagination_token = None
    while True:
        kwargs = {"UserPoolId": user_pool_id, "Limit": 60}
        if pagination_token:
            kwargs["PaginationToken"] = pagination_token
        resp = client.list_users(**kwargs)
        for u in resp.get("Users", []):
            for attr in u.get("Attributes", []):
                if attr.get("Name") == "email" and (attr.get("Value") or "").strip().lower() == want:
                    return u["Username"]
        pagination_token = resp.get("PaginationToken")
        if not pagination_token:
            break
    return None


def ensure_superuser(
    user_pool_id: str,
    email: str,
    password: str | None = None,
    set_role_only: bool = False,
    region: str = "ap-south-1",
) -> str:
    """
    Create or update a Cognito user with custom:role=superuser.

    :param user_pool_id: Cognito User Pool ID
    :param email: User email (used as username)
    :param password: Permanent password (required unless set_role_only and user exists)
    :param set_role_only: If True, only update custom:role; do not set password (user must already exist)
    :param region: AWS region
    :return: Message string (e.g. "Created" or "Updated")
    :raises: RuntimeError on failure
    """
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 is required. Install with: pip install boto3") from None

    client = boto3.client("cognito-idp", region_name=region)
    email_norm = email.strip().lower()
    uses_email_alias = _pool_uses_email_alias(client, user_pool_id)

    # Internal Cognito Username: for email-alias pools use UUID (Cognito rejects email-like formats); otherwise email.
    if uses_email_alias:
        cognito_username_create = str(uuid.uuid4())
    else:
        cognito_username_create = email_norm

    user_attributes = [
        {"Name": "email", "Value": email_norm},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:role", "Value": "superuser"},
    ]

    # Resolve existing user's Cognito Username (for email-alias pools find by email)
    cognito_username: str | None = None
    if uses_email_alias:
        cognito_username = _find_username_by_email(client, user_pool_id, email_norm)
        if cognito_username is None:
            try:
                client.admin_get_user(UserPoolId=user_pool_id, Username=cognito_username_create)
                cognito_username = cognito_username_create
            except client.exceptions.UserNotFoundException:
                pass
    else:
        try:
            client.admin_get_user(UserPoolId=user_pool_id, Username=email_norm)
            cognito_username = email_norm
        except client.exceptions.UserNotFoundException:
            pass

    user_exists = cognito_username is not None

    if user_exists:
        if set_role_only:
            client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=cognito_username,
                UserAttributes=[
                    {"Name": "custom:role", "Value": "superuser"},
                ],
            )
            return "Updated existing user to superuser role (custom:role=superuser)."
        # Update role and optionally set new password
        client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=cognito_username,
            UserAttributes=[{"Name": "custom:role", "Value": "superuser"}],
        )
        if password:
            client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=cognito_username,
                Password=password,
                Permanent=True,
            )
            return "Updated existing user to superuser role and set new password."
        return "Updated existing user to superuser role (password unchanged)."

    # Create new user
    if not password:
        raise RuntimeError("Password required when creating a new user (or use --set-role-only for existing user).")

    client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=cognito_username_create,
        UserAttributes=user_attributes,
        TemporaryPassword=password,
        MessageAction="SUPPRESS",
    )
    # Set permanent password immediately so user is not forced to change on first login
    client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=cognito_username_create,
        Password=password,
        Permanent=True,
    )
    return "Created new superuser and set permanent password."


def ensure_user_with_role(
    user_pool_id: str,
    email: str,
    role: str,
    password: str | None = None,
    set_role_only: bool = False,
    region: str = "ap-south-1",
) -> str:
    """
    Create or update a Cognito user with custom:role=<role> (e.g. superuser, patient).

    :param user_pool_id: Cognito User Pool ID
    :param email: User email (used as username/alias)
    :param role: Value for custom:role (e.g. "superuser", "patient")
    :param password: Permanent password (required unless set_role_only and user exists)
    :param set_role_only: If True, only update custom:role
    :param region: AWS region
    :return: Message string
    """
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 is required. Install with: pip install boto3") from None

    client = boto3.client("cognito-idp", region_name=region)
    email_norm = email.strip().lower()
    uses_email_alias = _pool_uses_email_alias(client, user_pool_id)

    if uses_email_alias:
        cognito_username_create = str(uuid.uuid4())
    else:
        cognito_username_create = email_norm

    user_attributes = [
        {"Name": "email", "Value": email_norm},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:role", "Value": role},
    ]

    cognito_username: str | None = None
    if uses_email_alias:
        cognito_username = _find_username_by_email(client, user_pool_id, email_norm)
        if cognito_username is None:
            try:
                client.admin_get_user(UserPoolId=user_pool_id, Username=cognito_username_create)
                cognito_username = cognito_username_create
            except client.exceptions.UserNotFoundException:
                pass
    else:
        try:
            client.admin_get_user(UserPoolId=user_pool_id, Username=email_norm)
            cognito_username = email_norm
        except client.exceptions.UserNotFoundException:
            pass

    user_exists = cognito_username is not None

    if user_exists:
        if set_role_only:
            client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=cognito_username,
                UserAttributes=[{"Name": "custom:role", "Value": role}],
            )
            return f"Updated existing user to role {role!r}."
        client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=cognito_username,
            UserAttributes=[{"Name": "custom:role", "Value": role}],
        )
        if password:
            client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=cognito_username,
                Password=password,
                Permanent=True,
            )
            return f"Updated existing user to role {role!r} and set new password."
        return f"Updated existing user to role {role!r} (password unchanged)."

    if not password:
        raise RuntimeError("Password required when creating a new user (or use --set-role-only for existing user).")

    client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=cognito_username_create,
        UserAttributes=user_attributes,
        TemporaryPassword=password,
        MessageAction="SUPPRESS",
    )
    client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=cognito_username_create,
        Password=password,
        Permanent=True,
    )
    return f"Created new user with role {role!r} and set permanent password."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or update a Cognito user with superuser role (no console).",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("SUPERUSER_EMAIL", "superuser@cdss.ai"),
        help="User email (Username in Cognito). Default: superuser@cdss.ai or SUPERUSER_EMAIL",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SUPERUSER_PASSWORD", ""),
        help="Password (required for new user). Use SUPERUSER_PASSWORD in CI.",
    )
    parser.add_argument(
        "--user-pool-id",
        default=(
            os.environ.get("COGNITO_USER_POOL_ID")
            or _get_user_pool_id_from_terraform()
            or _get_user_pool_id_from_secrets()
        ),
        help="Cognito User Pool ID (default: env, Terraform output, or app-config secret)",
    )
    parser.add_argument(
        "--set-role-only",
        action="store_true",
        help="Only set custom:role=superuser on an existing user; do not create or change password",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "ap-south-1"),
        help="AWS region (default: ap-south-1)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Create/update the standard demo user for the deployed dashboard (demo@cdss.ai). Use these credentials on the deployed login page.",
    )
    parser.add_argument(
        "--demo-patient",
        action="store_true",
        help="Create/update the demo patient user (patient@cdss.ai). Patient logs in on the same portal and is redirected to the patient dashboard.",
    )
    args = parser.parse_args()

    # Demo user: require env so no credentials in repo
    DEMO_EMAIL = "demo@cdss.ai"
    DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD")
    PATIENT_EMAIL = "patient@cdss.ai"
    PATIENT_PASSWORD = os.environ.get("PATIENT_DEMO_PASSWORD")

    user_pool_id = (args.user_pool_id or "").strip()
    email = (args.email or "").strip()
    password = (args.password or "").strip() or None

    if args.demo:
        email = DEMO_EMAIL
        password = DEMO_PASSWORD
        if not password:
            print("Error: Set DEMO_PASSWORD in env when using --demo (do not commit credentials).", file=sys.stderr)
            return 1

    # Create demo patient user (same portal, redirects to patient dashboard)
    if args.demo_patient:
        if not PATIENT_PASSWORD:
            print("Error: Set PATIENT_DEMO_PASSWORD in env when using --demo-patient (do not commit credentials).", file=sys.stderr)
            return 1
        if not user_pool_id:
            print(
                "Error: Cognito User Pool ID required. Set COGNITO_USER_POOL_ID or run from repo with Terraform state, or pass --user-pool-id.",
                file=sys.stderr,
            )
            return 1
        try:
            msg = ensure_user_with_role(
                user_pool_id=user_pool_id,
                email=PATIENT_EMAIL,
                role="patient",
                password=PATIENT_PASSWORD,
                set_role_only=False,
                region=args.region,
            )
            print(msg)
            print(f"  User: {PATIENT_EMAIL}")
            print(f"  Pool: {user_pool_id}")
            print("")
            print("  Patient login (same portal URL):")
            print(f"    User ID:  {PATIENT_EMAIL}")
            print("    Password: (set via PATIENT_DEMO_PASSWORD)")
            print("  After login you are redirected to the patient dashboard.")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if not user_pool_id:
        print(
            "Error: Cognito User Pool ID required. Set COGNITO_USER_POOL_ID or run from repo with Terraform state, or pass --user-pool-id.",
            file=sys.stderr,
        )
        return 1
    if not email:
        print("Error: --email or SUPERUSER_EMAIL required.", file=sys.stderr)
        return 1
    if not args.set_role_only and not password:
        print(
            "Error: --password or SUPERUSER_PASSWORD required when creating a new user (omit --set-role-only to create).",
            file=sys.stderr,
        )
        return 1

    try:
        msg = ensure_superuser(
            user_pool_id=user_pool_id,
            email=email,
            password=password,
            set_role_only=args.set_role_only,
            region=args.region,
        )
        print(msg)
        print(f"  User: {email}")
        print(f"  Pool: {user_pool_id}")
        if args.demo:
            print("")
            print("  Demo login on your deployed dashboard:")
            print(f"    Email:    {email}")
            print("    Password: (set via DEMO_PASSWORD env)")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
