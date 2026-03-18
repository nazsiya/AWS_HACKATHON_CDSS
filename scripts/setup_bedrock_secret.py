#!/usr/bin/env python3
"""
Create or update the Bedrock config secret in AWS Secrets Manager for local/deployed API.

Run from repo root with AWS credentials configured (aws configure or env vars):
  python scripts/setup_bedrock_secret.py

Optional env:
  AWS_REGION          default ap-south-1
  BEDROCK_SECRET_NAME default cdss-dev/bedrock-config (or from config.json)
  BEDROCK_MODEL_ID    default apac.amazon.nova-lite-v1:0
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_JSON = REPO_ROOT / "config.json"


def get_secret_name() -> str:
    if os.environ.get("BEDROCK_SECRET_NAME"):
        return os.environ["BEDROCK_SECRET_NAME"].strip()
    if CONFIG_JSON.exists():
        try:
            cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
            name = (cfg.get("bedrock_config_secret_name") or "").strip()
            if name:
                return name
        except Exception:
            pass
    return "cdss-dev/bedrock-config"


def main() -> int:
    region = (os.environ.get("AWS_REGION") or "ap-south-1").strip()
    model_id = (os.environ.get("BEDROCK_MODEL_ID") or "apac.amazon.nova-lite-v1:0").strip()
    secret_name = get_secret_name()

    payload = {
        "model_id": model_id,
        "region": region,
    }
    secret_string = json.dumps(payload, indent=2)

    print("Bedrock secret setup")
    print(f"  Region:      {region}")
    print(f"  Secret name: {secret_name}")
    print(f"  Model ID:   {model_id}")
    print()

    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=region)

        try:
            client.get_secret_value(SecretId=secret_name)
            client.put_secret_value(SecretId=secret_name, SecretString=secret_string)
            print(f"Updated existing secret: {secret_name}")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ResourceNotFoundException":
                client.create_secret(Name=secret_name, SecretString=secret_string)
                print(f"Created new secret: {secret_name}")
            else:
                raise

        print()
        print("Next steps:")
        print("  1. In AWS Console -> Amazon Bedrock -> Model access (region ap-south-1), enable the model if needed:")
        if "nova-lite" in model_id:
            print("     - Amazon Nova Lite")
        elif "claude" in model_id.lower():
            print("     - Claude 3 Haiku (or the model you set)")
        print("  2. Restart your local API: python scripts/run_api_local.py")
        print("  3. Test AI: open dashboard -> AI, send a message, or run: python scripts/verify_phase4_ai.py")
        return 0

    except ImportError:
        print("Error: boto3 is required. Install with: pip install boto3")
        return 1
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", str(e))
        print(f"AWS error ({code}): {msg}")
        print("  Ensure AWS credentials are configured: aws configure  or  set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
