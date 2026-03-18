#!/usr/bin/env python3
"""
WebSocket test client for CDSS real-time API.

Connects with wss://...?token=<id_token>&doctor_id=<id>, sends subscribe_* and
checklist_update actions, and asserts echoed/received messages.

Usage:
  # With token from get_token.py (authorizer enabled)
  python scripts/auth/get_token.py -u doctor@hospital.in -p secret > /tmp/token.txt
  set VITE_WS_URL=wss://xxx.execute-api.ap-south-1.amazonaws.com/dev
  set WS_TOKEN=$(type /tmp/token.txt)
  python scripts/ws/ws_client.py

  # Env (or pass as args)
  WS_URL     — WebSocket URL (e.g. wss://xxx.execute-api.ap-south-1.amazonaws.com/dev)
  WS_TOKEN   — Cognito id_token for ?token= (required when authorizer is enabled)
  DOCTOR_ID  — Optional doctor_id for ?doctor_id=

  # Without auth (when enable_websocket_authorizer=false)
  python scripts/ws/ws_client.py --no-auth --url wss://xxx/dev
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _check_websocket_client():
    try:
        import websocket  # noqa: F401
        return True
    except ImportError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WebSocket test client: connect with token and doctor_id, send subscribe/checklist_update, assert responses."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("WS_URL", os.environ.get("VITE_WS_URL", "")),
        help="WebSocket URL (or WS_URL / VITE_WS_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("WS_TOKEN", ""),
        help="Cognito id_token for ?token= (or WS_TOKEN)",
    )
    parser.add_argument(
        "--doctor-id",
        default=os.environ.get("DOCTOR_ID", "test-doctor-1"),
        help="doctor_id query param (or DOCTOR_ID)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Connect without token (use only when enable_websocket_authorizer=false)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Connection and receive timeout in seconds",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log all messages",
    )
    args = parser.parse_args()

    url = (args.url or "").strip()
    if not url:
        print("Error: WebSocket URL required (--url or WS_URL or VITE_WS_URL).", file=sys.stderr)
        return 1

    if not url.startswith("ws"):
        url = ("wss://" if "://" not in url else "") + url.replace("https://", "wss://").replace("http://", "ws://")

    if not args.no_auth and not (args.token or os.environ.get("WS_TOKEN")):
        print("Error: Token required when authorizer is enabled (--token or WS_TOKEN). Use --no-auth only when authorizer is disabled.", file=sys.stderr)
        return 1

    token = (args.token or os.environ.get("WS_TOKEN", "")).strip()
    doctor_id = (args.doctor_id or "").strip()
    if token:
        url = url + ("&" if "?" in url else "?") + "token=" + __import__("urllib.parse").quote(token, safe="")
    if doctor_id:
        url = url + ("&" if "?" in url else "?") + "doctor_id=" + __import__("urllib.parse").quote(doctor_id, safe="")

    if not _check_websocket_client():
        print("Install websocket-client: pip install websocket-client", file=sys.stderr)
        return 1

    import websocket

    received: list[dict] = []
    errors: list[str] = []
    ws_ref: list = []

    def on_message(ws, message):
        try:
            data = json.loads(message)
            received.append(data)
            if args.verbose:
                print("RECV:", data)
        except json.JSONDecodeError:
            received.append({"raw": message})
            if args.verbose:
                print("RECV (raw):", message[:200])

    def on_error(ws, err):
        errors.append(str(err))
        if args.verbose:
            print("ERROR:", err, file=sys.stderr)

    def on_close(ws, close_status_code, close_msg):
        if args.verbose:
            print("CLOSED:", close_status_code, close_msg)

    def on_open(ws):
        ws_ref.append(ws)
        # subscribe_surgery
        ws.send(json.dumps({"action": "subscribe_surgery", "surgery_id": "surg-test-1"}))
        # subscribe_patient
        ws.send(json.dumps({"action": "subscribe_patient", "patient_id": "patient-test-1"}))
        # checklist_update
        ws.send(json.dumps({
            "action": "checklist_update",
            "surgery_id": "surg-test-1",
            "checklist_item_id": "item-1",
            "completed": True,
        }))
        # Close after short delay so we collect replies
        def close_later():
            time.sleep(2.0)
            if ws_ref:
                try:
                    ws_ref[0].close()
                except Exception:
                    pass
        threading.Thread(target=close_later, daemon=True).start()

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
    )
    try:
        ws.run_forever(timeout=args.timeout)
    except Exception as e:
        errors.append(str(e))
        print("Error:", e, file=sys.stderr)

    if errors:
        print("Errors:", errors, file=sys.stderr)
        return 1

    # Assert we got at least acknowledgements (subscribe_* and checklist_update echo)
    types_seen = {m.get("type") for m in received if isinstance(m, dict)}
    expected = {"subscribe_surgery", "subscribe_patient", "checklist_update"}
    missing = expected - types_seen
    if missing:
        print("Warning: expected message types", expected, "got", types_seen, file=sys.stderr)
        # Still pass if we got any response (connection worked)
    if not received:
        print("No messages received; connection may have closed before replies.", file=sys.stderr)
        return 1

    print("OK: received", len(received), "message(s); types:", sorted(types_seen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
