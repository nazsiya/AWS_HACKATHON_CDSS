"""
Bedrock client for Claude 3 Haiku (NLP core).
Uses boto3 Bedrock Runtime in ap-south-1.
"""

from typing import Any, Optional

from cdss.core.config import get_config


def get_bedrock_client() -> Any:
    """Return Bedrock Runtime client (lazy import to avoid Lambda cold-start impact)."""
    import boto3

    config = get_config()
    return boto3.client("bedrock-runtime", region_name=config.aws_region)


def invoke_converse(
    model_id: str,
    system_prompt: str,
    user_message: str,
    *,
    max_tokens: int = 1024,
    tool_config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Invoke Bedrock Converse API (or InvokeModel for Claude).
    Placeholder: implement with actual Bedrock Converse/InvokeModel when wiring.
    """
    client = get_bedrock_client()
    config = get_config()
    mid = model_id or config.bedrock_model_id
    # TODO: use client.converse() or invoke_model with correct payload
    return {"response": "", "model_id": mid, "system_prompt_preview": system_prompt[:100]}
