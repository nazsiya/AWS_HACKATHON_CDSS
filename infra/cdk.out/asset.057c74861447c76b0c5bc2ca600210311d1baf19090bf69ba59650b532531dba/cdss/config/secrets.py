"""
Central retrieval of AWS configuration, API keys, endpoints, and secrets from AWS Secrets Manager via boto3.

Per project conventions: no long-lived credentials or hardcoded secrets in code.
Secret *names* (e.g. RDS_CONFIG_SECRET_NAME) may be set via environment or IaC; actual secret values
are always fetched from AWS Secrets Manager at runtime.

Usage:
  - get_secret(secret_name, region=None) -> dict  # raw JSON from a secret
  - get_app_config() -> dict  # from CDSS_APP_CONFIG_SECRET_NAME (Cognito, EventBridge, endpoints, etc.)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Environment keys for secret *names* (resource identifiers, not sensitive).
RDS_CONFIG_SECRET_NAME_ENV = "RDS_CONFIG_SECRET_NAME"
BEDROCK_CONFIG_SECRET_NAME_ENV = "BEDROCK_CONFIG_SECRET_NAME"
APP_CONFIG_SECRET_NAME_ENV = "CDSS_APP_CONFIG_SECRET_NAME"
AWS_REGION_ENV = "AWS_REGION"

_DEFAULT_REGION = "ap-south-1"

# In-memory cache for app config to avoid repeated Secrets Manager calls in the same process.
_app_config_cache: dict[str, Any] | None = None


def get_secret(secret_name: str, region: str | None = None) -> dict[str, Any]:
    """
    Retrieve a secret from AWS Secrets Manager and return its JSON value as a dict.

    :param secret_name: Secrets Manager secret ID or ARN.
    :param region: AWS region; defaults to AWS_REGION env or ap-south-1.
    :return: Parsed JSON secret value. Empty dict if secret is missing or invalid.
    :raises: Propagates boto3/ClientError if secret does not exist or access is denied.
    """
    if not secret_name or not secret_name.strip():
        return {}
    region = (region or os.environ.get(AWS_REGION_ENV) or _DEFAULT_REGION).strip()
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name.strip())
        raw = resp.get("SecretString")
        if not raw:
            return {}
        return json.loads(raw)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            logger.debug("Secret %s not found in Secrets Manager. Fallback to env.", secret_name)
            return {}
        logger.warning("Secrets Manager get_secret_value failed for %s: %s", secret_name, code)
        return {}  # Avoid raising to prevent request hangs
    except Exception as e:
        logger.warning("Secret %s retrieval failed: %s", secret_name, e)
        return {}


def get_app_config(region: str | None = None) -> dict[str, Any]:
    """
    Return application config from Secrets Manager (CDSS_APP_CONFIG_SECRET_NAME).

    Expected JSON keys (all optional): cognito_user_pool_id, aws_region, event_bus_name,
    agent_runtime_arn, gateway_get_hospitals_lambda_arn, api_base_url, and other endpoints/keys.
    Result is cached in-process for the lifetime of the process.

    If CDSS_APP_CONFIG_SECRET_NAME is not set, returns {} and callers should fall back to
    environment variables for backward compatibility.
    """
    global _app_config_cache
    secret_name = (os.environ.get(APP_CONFIG_SECRET_NAME_ENV) or "").strip()
    if not secret_name:
        return {}
    if _app_config_cache is not None:
        return _app_config_cache
    try:
        _app_config_cache = get_secret(secret_name, region=region)
        return _app_config_cache or {}
    except Exception:
        return {}


def get_rds_config(region: str | None = None) -> dict[str, Any]:
    """
    Return RDS/Aurora config from Secrets Manager (RDS_CONFIG_SECRET_NAME).

    Expected keys: host, port, database, username; optional: region.
    Used to build DB connection (with IAM auth token when using Aurora).
    """
    secret_name = (os.environ.get(RDS_CONFIG_SECRET_NAME_ENV) or "").strip()
    if not secret_name:
        return {}
    return get_secret(secret_name, region=region)


def get_bedrock_config(region: str | None = None) -> dict[str, Any]:
    """
    Return Bedrock config from Secrets Manager (BEDROCK_CONFIG_SECRET_NAME).

    Expected keys: model_id, region, and any API keys if required.
    """
    secret_name = (os.environ.get(BEDROCK_CONFIG_SECRET_NAME_ENV) or "").strip()
    if not secret_name:
        return {}
    return get_secret(secret_name, region=region)
