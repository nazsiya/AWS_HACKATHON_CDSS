"""
Load Bedrock configuration from AWS Secrets Manager.

Expects secret JSON: region, model_id. No credentials; use IAM role for bedrock:InvokeModel.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def get_bedrock_config(secret_name: str | None = None) -> dict[str, Any]:
    """
    Load Bedrock config from Secrets Manager.

    Expects secret JSON: region, model_id (e.g. anthropic.claude-3-haiku-20240307-v1:0).
    Uses IAM role; no API keys in secret.

    Returns:
        dict with keys: region, model_id.

    Raises:
        ValueError: If secret not set, not found, or missing keys.
    """
    import boto3
    from botocore.exceptions import ClientError

    name = secret_name or os.environ.get("BEDROCK_CONFIG_SECRET_NAME")
    if not name:
        raise ValueError("BEDROCK_CONFIG_SECRET_NAME not set; cannot load Bedrock config")

    client = boto3.client("secretsmanager")
    try:
        resp = client.get_secret_value(SecretId=name)
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "")
        logger.error(
            "Secrets Manager get_secret_value failed (bedrock_config)",
            extra={"secret_name": name, "error_code": err_code},
        )
        if err_code == "ResourceNotFoundException":
            raise ValueError(
                f"Secret '{name}' not found. Run Terraform apply or set BEDROCK_CONFIG_SECRET_NAME."
            ) from e
        raise

    raw = resp.get("SecretString")
    if not raw:
        raise ValueError("Bedrock config secret has no SecretString")
    config = json.loads(raw)
    for key in ("region", "model_id"):
        if key not in config:
            raise ValueError(f"Bedrock config missing key: {key}")
    return config
