#!/usr/bin/env python3
r"""
Interactive chat with the CDSS agent (Bedrock + database).
Run the local API server first (with DATABASE_URL and BEDROCK_CONFIG_SECRET_NAME),
then run this script and type messages; each is sent to POST /agent and the reply is printed.

Usage (from repo root):
  Terminal 1: .\scripts\start_ssm_tunnel.ps1
  Terminal 2: $env:DATABASE_URL="..."; $env:BEDROCK_CONFIG_SECRET_NAME="cdss-dev/bedrock-config"; $env:AWS_REGION="ap-south-1"; $env:PYTHONPATH="src"; python scripts/run_api_local.py
  Terminal 3: python scripts/chat_agent_interactive.py

Type your message and press Enter. Empty line or Ctrl+C to exit.
"""
from __future__ import annotations

import json
import os
import sys

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except ImportError:
    Request, urlopen, URLError, HTTPError = None, None, None, None  # type: ignore[misc, assignment]

DEFAULT_AGENT_URL = "http://localhost:8080/agent"


def post_agent(message: str, base_url: str) -> dict:
    """POST message to /agent; return parsed JSON body."""
    url = base_url.rstrip("/") if "/agent" in base_url else f"{base_url.rstrip('/')}/agent"
    payload = json.dumps({"message": message}).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def main() -> int:
    base_url = os.environ.get("CDSS_AGENT_URL", DEFAULT_AGENT_URL)
    print("CDSS Agent chat (Bedrock + DB). Send to:", base_url)
    print("Type a message and press Enter. Empty line to exit.")
    print("-" * 60)

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
            raw = post_agent(line, base_url)
        except URLError as e:
            print("Error: Cannot reach agent server.", e)
            print("  Start it with: run_api_local.py (and tunnel + DATABASE_URL + BEDROCK_CONFIG_SECRET_NAME)")
            continue
        except HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                print("Error:", err_json.get("error", err_body))
            except Exception:
                print("Error:", e.code, e.reason)
            continue
        except Exception as e:
            print("Error:", e)
            continue

        # Response shape: { "intent", "agent", "data", "safety_disclaimer", "source", "duration_ms" } or Lambda wrapper with body
        body = raw
        if isinstance(raw.get("body"), str):
            try:
                body = json.loads(raw["body"])
            except json.JSONDecodeError:
                body = raw
        status = raw.get("statusCode", 200)
        if status != 200:
            print("Error:", body.get("error", body))
            continue

        intent = body.get("intent", "")
        data = body.get("data") or {}
        reply = data.get("reply") if isinstance(data, dict) else str(data)
        disclaimer = body.get("safety_disclaimer", "")
        source = body.get("source", "")
        duration_ms = body.get("duration_ms", 0)

        if intent:
            print(f"[{intent}] ", end="")
        if reply:
            print(reply)
        elif isinstance(data, dict) and data:
            print(json.dumps(data, indent=2, default=str))
        else:
            print("(No reply text)")
        if disclaimer:
            print("  —", disclaimer)
        print(f"  (source={source}, {duration_ms} ms)")
        print()


if __name__ == "__main__":
    sys.exit(main() or 0)
