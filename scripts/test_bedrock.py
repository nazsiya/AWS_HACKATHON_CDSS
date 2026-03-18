#!/usr/bin/env python3
"""
Test Bedrock connectivity and run interactive prompts.
Usage:
  python scripts/test_bedrock.py              # interactive: type a prompt, get response; empty line to exit
  python scripts/test_bedrock.py "Your prompt" # single prompt from command line
"""
import os
import sys

import boto3


def get_bedrock_config():
    """Region and model from env or defaults."""
    region = os.environ.get("AWS_REGION", "ap-south-1")
    model_id = os.environ.get("BEDROCK_MODEL_ID", "apac.amazon.nova-lite-v1:0")
    return region, model_id


def invoke_bedrock(prompt: str, region: str, model_id: str, max_tokens: int = 512) -> str:
    """Send prompt to Bedrock Converse; return response text or raise."""
    bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name=region)
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.5},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    if not content:
        return ""
    return content[0].get("text", "").strip()


def list_profiles(region: str) -> None:
    """List inference profiles in the region (optional)."""
    try:
        bedrock = boto3.client(service_name="bedrock", region_name=region)
        profiles = bedrock.list_inference_profiles()
        for p in profiles.get("inferenceProfileSummaries", []):
            print(f"  Profile: {p.get('inferenceProfileName')} ({p.get('inferenceProfileId')})")
    except Exception as e:
        print(f"  (Could not list profiles: {e})")


def main() -> int:
    region, model_id = get_bedrock_config()
    print(f"Bedrock test — region: {region}, model: {model_id}")
    print("Listing inference profiles...")
    list_profiles(region)

    # Single prompt from command line
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:]).strip()
        if not prompt:
            print("Usage: python scripts/test_bedrock.py [prompt]")
            return 1
        try:
            print(f"\nYou: {prompt}")
            reply = invoke_bedrock(prompt, region, model_id)
            print(f"Bedrock: {reply}")
        except Exception as e:
            print(f"Error: {e}")
            if "AccessDeniedException" in str(e):
                print("Hint: Enable model access in the Bedrock console for this region.")
            elif "ValidationException" in str(e):
                print("Hint: Check model ID and region.")
            return 1
        return 0

    # Interactive loop
    print("\n--- Interactive mode: type a prompt and press Enter. Empty line to exit. ---\n")
    try:
        while True:
            try:
                line = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return 0
            if not line:
                print("Bye.")
                return 0
            try:
                reply = invoke_bedrock(line, region, model_id)
                print(f"Bedrock: {reply}\n")
            except Exception as e:
                print(f"Error: {e}\n")
                if "AccessDeniedException" in str(e):
                    print("Hint: Enable model access in the Bedrock console for this region.\n")
    except KeyboardInterrupt:
        print("\nBye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
