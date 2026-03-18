#!/usr/bin/env python3
"""
Phase 1.1: Verify a Bedrock model (ap-south-1) is enabled and returns tool-use.

Tries Amazon Nova Lite first, then multiple Anthropic Claude models; reports which work.
Run after enabling models in AWS Console -> Bedrock -> Model access.

Usage:
  # From repo root: try default list and report which models work
  AWS_REGION=ap-south-1 python scripts/verify_bedrock_haiku_tool_use.py

  # Try all models and show full report (same when no env/secret set)
  BEDROCK_VERIFY_SCAN=1 AWS_REGION=ap-south-1 python scripts/verify_bedrock_haiku_tool_use.py

  # Prefer a specific model only (PowerShell):
  $env:BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
  python scripts/verify_bedrock_haiku_tool_use.py
"""
from __future__ import annotations

import json
import os
import sys

# Amazon models (often available without payment)
AMAZON_MODELS = [
    "apac.amazon.nova-lite-v1:0",
    "amazon.nova-lite-v1:0",
]

# Anthropic Claude models (order: lighter/cheaper first; exact Bedrock IDs)
ANTHROPIC_MODELS = [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0",
]

MODELS_TO_TRY = AMAZON_MODELS + ANTHROPIC_MODELS


def get_models_to_try() -> list[str]:
    """Ordered list of model IDs: env/secret first, then fallback to full list so at least one may work."""
    region = os.environ.get("AWS_REGION", "ap-south-1")
    # Single model from env -> try it first, then fall back to others if it fails (e.g. payment)
    env_model = (os.environ.get("BEDROCK_MODEL_ID") or "").strip()
    if env_model:
        return [env_model] + [m for m in MODELS_TO_TRY if m != env_model]
    # From secret: try secret model first, then rest of list
    secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME", "").strip()
    if secret_name:
        try:
            import boto3
            sm = boto3.client("secretsmanager", region_name=region)
            raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
            cfg = json.loads(raw)
            mid = (cfg.get("model_id") or "").strip()
            if mid:
                return [mid] + [m for m in MODELS_TO_TRY if m != mid]
        except Exception as e:
            print(f"Warning: could not read secret {secret_name}: {e}")
    # No env/secret: try full list and report which work (scan mode)
    return MODELS_TO_TRY


def main() -> int:
    region = os.environ.get("AWS_REGION", "ap-south-1")
    models = get_models_to_try()
    print(f"Verifying Bedrock tool-use — region={region}")
    print(f"  Models to try: {models}")

    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "get_patient_summary",
                    "description": "Get a brief clinical summary for a patient by ID.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "patient_id": {"type": "string", "description": "Patient ID e.g. PT-1001"},
                            },
                            "required": ["patient_id"],
                        }
                    },
                }
            }
        ],
        "toolChoice": {"auto": {}},
    }

    messages = [
        {
            "role": "user",
            "content": [
                {"text": "Get a patient summary for patient ID PT-1001. Call the get_patient_summary tool."},
            ],
        },
    ]

    import boto3
    client = boto3.client("bedrock-runtime", region_name=region)
    last_err = None
    working: list[str] = []
    failed: list[tuple[str, str]] = []
    scan_mode = len(models) > 1
    requested_model = (os.environ.get("BEDROCK_MODEL_ID") or "").strip() or None

    for model_id in models:
        print(f"\n  Trying model_id={model_id} ...")
        try:
            response = client.converse(
                modelId=model_id,
                messages=messages,
                inferenceConfig={"maxTokens": 512, "temperature": 0.0},
                toolConfig=tool_config,
            )
        except Exception as e:
            err = str(e)
            last_err = e
            short = err.split(":")[-1].strip() if ":" in err else err[:60]
            failed.append((model_id, short))
            if "AccessDeniedException" in err or "ResourceNotFoundException" in err:
                print(f"    Skip: {err[:80]}...")
                continue
            print(f"    Error: {err[:120]}")
            continue

        stop_reason = response.get("stopReason", "")
        content = response.get("output", {}).get("message", {}).get("content", [])

        tool_uses = [c for c in content if c.get("type") == "tool_use" or "toolUse" in c]
        if not tool_uses:
            for c in content:
                if isinstance(c, dict) and ("name" in c and "input" in c and ("id" in c or "toolUseId" in c)):
                    tool_uses.append(c)

        print(f"    stopReason: {stop_reason}, content blocks: {len(content)}, tool_use: {len(tool_uses)}")

        if stop_reason == "tool_use" and len(tool_uses) >= 1:
            working.append(model_id)
            print(f"    OK: tool-use returned.")
            if not scan_mode:
                print(f"\n  OK: {model_id} returned tool-use. Phase 1.1 verified.")
                if tool_uses:
                    t = tool_uses[0]
                    print(f"  Tool: {t.get('name', t.get('toolUse', {}).get('name', '?'))}")
                return 0
            continue

        if tool_uses:
            working.append(model_id)
            print(f"    OK: tool-use blocks present.")
            if not scan_mode:
                print(f"\n  OK: {model_id} returned tool-use blocks. Phase 1.1 verified.")
                return 0
            continue

        failed.append((model_id, "No tool_use in response (model replied with text)"))
        print(f"    No tool_use in response (model may have replied with text).")

    # Summary when we tried multiple models
    if scan_mode:
        print("\n" + "=" * 60)
        print("SUMMARY: Models that support tool-use (working)")
        if working:
            for m in working:
                print(f"  + {m}")
        else:
            print("  (none)")
        print("\nModels not available or no tool-use")
        for m, reason in failed:
            print(f"  - {m}")
            print(f"    {reason[:70]}")
        print("=" * 60)
        if working:
            print(f"\nPhase 1.1 verified. Working models: {', '.join(working)}")
            if requested_model and requested_model not in working and any(f[0] == requested_model for f in failed):
                print(f"  Note: Requested model ({requested_model}) not available (enable in Bedrock or add payment); used a fallback above.")
            return 0
    else:
        print("\nFAIL: No model returned tool-use.")
        if last_err:
            err = str(last_err)
            print(f"  Last error: {err[:200]}")
            if "AccessDeniedException" in err:
                print("  -> Enable a model (e.g. Nova Lite or Claude) in Bedrock -> Model access (ap-south-1).")
            if "INVALID_PAYMENT_INSTRUMENT" in err or "payment instrument" in err.lower():
                print("  -> Add a valid payment method in AWS, or use Amazon Nova Lite (often available without).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
