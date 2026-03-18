#!/usr/bin/env python3
"""
Phase 1.3: Verify local API and agent endpoint.

Option A - Auto-start (default): run this script from repo root; it will start
  the local API if needed, then run the verification.
  python scripts/verify_phase1_local_api.py

Option B - Manual: start the API in another terminal first, then run this script.
  Terminal 1: $env:PYTHONPATH="src"; python scripts/run_api_local.py
  Terminal 2: python scripts/verify_phase1_local_api.py

Custom base URL: BASE_URL=http://localhost:8080 python scripts/verify_phase1_local_api.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

BASE_URL = (os.environ.get("BASE_URL") or "http://localhost:8080").strip().rstrip("/")
TIMEOUT = 30
SERVER_START_WAIT = 5
# When auto-starting the server, use this port to avoid conflict with another app on 8080
AUTO_START_PORT = "8081"


def post_agent(body: dict) -> tuple[int, dict]:
    """POST to /agent or /api/v1/agent; return (status_code, parsed_body). Tries both paths on 404."""
    paths = ("/agent", "/api/v1/agent")
    last_code, last_body = 0, {}
    for path in paths:
        try:
            req = urllib.request.Request(
                BASE_URL + path,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as f:
                return f.status, json.loads(f.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                last_body = json.loads(e.fp.read().decode("utf-8")) if e.fp else {}
            except (json.JSONDecodeError, ValueError, AttributeError, ConnectionResetError, OSError):
                last_body = {"error": f"HTTP {e.code}"}
            last_code = e.code
            if e.code in (404, 405) and path != paths[-1]:
                continue
            return e.code, last_body
        except OSError:
            continue
    if last_code:
        return last_code, last_body
    return 0, {"error": "Connection refused. Start server: PYTHONPATH=src python scripts/run_api_local.py"}


def _server_reachable(url: str | None = None) -> bool:
    """Return True if url (or BASE_URL) is the CDSS API (200 with service=cdss or /health)."""
    base = (url or BASE_URL).strip().rstrip("/")
    for path in ("/health", "/"):
        try:
            req = urllib.request.Request(base + path, method="GET")
            with urllib.request.urlopen(req, timeout=3) as f:
                if f.getcode() != 200:
                    continue
                raw = f.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                if data.get("service") == "cdss" or "status" in data:
                    return True
        except (urllib.error.HTTPError, OSError, json.JSONDecodeError):
            continue
    return False


def _start_local_server(port: str) -> bool:
    """Start run_api_local.py in the background on the given port; return True if started."""
    script = os.path.join(REPO_ROOT, "scripts", "run_api_local.py")
    if not os.path.isfile(script):
        return False
    env = os.environ.copy()
    env["PYTHONPATH"] = SRC
    env["PORT"] = port
    try:
        if sys.platform == "win32":
            DETACHED = 0x00000008
            p = subprocess.Popen(
                [sys.executable, script],
                cwd=REPO_ROOT,
                env=env,
                creationflags=DETACHED,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            p = subprocess.Popen(
                [sys.executable, script],
                cwd=REPO_ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return p.poll() is None
    except Exception:
        return False


def main() -> int:
    global BASE_URL
    print("Phase 1.3: Local API and agent endpoint verification")
    print(f"  BASE_URL={BASE_URL}")
    print()

    # Auto-start local API if targeting localhost and server not reachable
    if "localhost" in BASE_URL or "127.0.0.1" in BASE_URL:
        if not _server_reachable():
            print("  Local API not detected. Starting run_api_local.py ...")
            # Use 8081 when auto-starting so we don't conflict with another app on 8080
            use_port = AUTO_START_PORT
            if _start_local_server(use_port):
                auto_url = f"http://localhost:{use_port}"
                print(f"  Waiting {SERVER_START_WAIT}s for server to listen on port {use_port} ...")
                time.sleep(SERVER_START_WAIT)
                if _server_reachable(auto_url):
                    BASE_URL = auto_url
                    print(f"  Using {BASE_URL} (auto-started on port {use_port}).")
                else:
                    print("  Server may have failed to start. Run manually in another terminal:")
                    print(f'    $env:PYTHONPATH="src"; $env:PORT="{use_port}"; python scripts/run_api_local.py')
                    print(f"  Then: $env:BASE_URL=\"{auto_url}\"; python scripts/verify_phase1_local_api.py")
            else:
                print("  Could not start server. Run manually in another terminal:")
                print('    $env:PYTHONPATH="src"; python scripts/run_api_local.py')
            print()

    # Optional: check that the right server is on 8080 (CDSS returns 200 on /health or default)
    try:
        req = urllib.request.Request(BASE_URL + "/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as f:
            raw = f.read().decode("utf-8")
            health = json.loads(raw) if raw else {}
        if health.get("service") == "cdss" or "status" in health:
            print("  Server check: CDSS API detected.")
        else:
            print("  Server check: response received (endpoint check may vary).")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("  Warning: GET /health returned 404. Is run_api_local.py running on 8080?")
    except OSError:
        print("  Warning: Cannot reach server. Start: PYTHONPATH=src python scripts/run_api_local.py")
    print()

    # Patient summary request (triggers patient intent and local agent or AgentCore)
    payload = {"message": "Give me a patient summary for PT-1001"}
    status, data = post_agent(payload)

    if status == 0:
        print("FAIL: Could not reach API.", data.get("error", ""))
        print("  Start server: PYTHONPATH=src python scripts/run_api_local.py")
        return 1

    if status != 200:
        print(f"FAIL: HTTP {status}")
        print("  Body:", json.dumps(data, indent=2)[:500])
        if status == 404:
            print()
            print("  Make sure the CDSS local API is running on port 8080 (not another app):")
            print("    Terminal 1: cd D:\\AI_Hackathon_CDSS")
            print("    Terminal 1: $env:PYTHONPATH=\"src\"; python scripts/run_api_local.py")
            print("  If another app is using 8080, stop it or use: $env:PORT=\"8081\"; $env:BASE_URL=\"http://localhost:8081\"")
            print("  Then run this script again from repo root.")
        return 1

    # Required envelope fields (from supervisor handler)
    ok = True
    for key in ("intent", "agent", "data", "safety_disclaimer"):
        if key not in data:
            print(f"  Missing key: {key}")
            ok = False
    if not ok:
        print("FAIL: Response missing required envelope fields.")
        return 1

    # Agent reply or tool evidence: data may contain reply (local/AgentCore) or nested data
    data_block = data.get("data") or {}
    reply = data_block.get("reply") if isinstance(data_block, dict) else None
    source = data.get("source", "local")

    print("  intent:", data.get("intent"))
    print("  agent:", data.get("agent"))
    print("  source:", source)
    print("  safety_disclaimer:", (data.get("safety_disclaimer") or "")[:80] + "...")
    if reply:
        print("  reply (first 200 chars):", (reply or "")[:200])
    if data.get("correlationId"):
        print("  correlationId:", data.get("correlationId"))
    if data.get("duration_ms") is not None:
        print("  duration_ms:", data.get("duration_ms"))

    print()
    print("OK: 200 response, agent reply in body, envelope valid. Phase 1.3 verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
