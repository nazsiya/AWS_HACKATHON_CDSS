"""
Minimal AgentCore Runtime agent for CDSS.

Entrypoint for direct code deployment. When invoked with {"prompt": "..."} or
structured payloads (e.g. {"severity": "high", "limit": 5}), it returns
stub responses that CDSS HTTP endpoints can use when use_agentcore=true.

Deploy: see agentcore/README.md and docs/agentcore-create-agents-in-aws.md.
"""

from __future__ import annotations

import json


def _handle(request: dict) -> dict:
    """Handle invocation: support supervisor, hospitals, and CDSS severity-assessment payloads."""
    prompt = request.get("prompt") or ""
    intent = request.get("intent") or ""
    severity = request.get("severity") or "medium"
    limit = request.get("limit", 5)
    patient_id = request.get("patient_id") or ""
    chief_complaint = request.get("chief_complaint") or ""

    # Supervisor-style request (intent-based routing from Supervisor agent)
    if intent:
        return _handle_by_intent(intent, prompt, patient_id, severity, limit, request)

    # Hospitals-style request
    if "hospital" in prompt.lower() or request.get("limit") is not None:
        return _handle_by_intent("hospitals", prompt, patient_id, severity, limit, request)
    # CDSS severity-assessment request (aligns with Telemedicine MCP Specialist escalation)
    if patient_id or chief_complaint or "triage" in prompt.lower() or "severity" in prompt.lower():
        return _handle_by_intent("triage", prompt, patient_id, severity, limit, request)
    # Generic prompt
    return {
        "intent": "general",
        "reply": "CDSS AgentCore agent ready. Send a message with context for routing.",
        "safety_disclaimer": "AI is for clinical support only.",
    }


def _handle_by_intent(intent: str, prompt: str, patient_id: str, severity: str, limit: int, request: dict) -> dict:
    """Route by intent label to produce stub/synthetic responses."""
    if intent == "hospitals":
        limit = min(max(1, int(limit)), 20)
        return {
            "intent": "hospitals",
            "hospitals": [
                {"id": f"H{i}", "name": f"Hospital {i} ({severity})", "distance_km": 2 + i, "available": True}
                for i in range(1, limit + 1)
            ],
            "safety_disclaimer": "Hospital availability is indicative. Confirm with facility. Not medical advice.",
        }
    if intent == "triage":
        return {
            "intent": "triage",
            "patient_id": patient_id or "unknown",
            "priority": "medium",
            "confidence": 0.7,
            "risk_factors": ["Stub from AgentCore Runtime; connect Gateway for full CDSS severity assessment."],
            "recommendations": ["Complete assessment when CDSS severity pipeline is configured."],
            "requires_senior_review": False,
            "safety_disclaimer": "Severity assessment is decision support only. Clinical decisions remain with the clinician.",
        }
    if intent == "patient":
        return {
            "intent": "patient",
            "patient_id": patient_id or "unknown",
            "reply": "Patient data retrieval via AgentCore. Connect Gateway for live data.",
            "safety_disclaimer": "AI is for clinical support only.",
        }
    if intent == "surgery":
        return {
            "intent": "surgery",
            "reply": "Surgery analysis via AgentCore. Connect Gateway for live checklist generation.",
            "safety_disclaimer": "AI is for clinical support only. Surgical decisions require qualified judgment.",
        }
    if intent in ("resource", "scheduling", "engagement"):
        return {
            "intent": intent,
            "reply": f"{intent.title()} agent via AgentCore. Connect Gateway for live data.",
            "safety_disclaimer": "AI is for clinical support only.",
        }
    # general
    return {
        "intent": intent or "general",
        "reply": "CDSS AgentCore agent received your request.",
        "safety_disclaimer": "AI is for clinical support only.",
    }


try:
    from bedrock_agentcore import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    @app.entrypoint
    def handler(request: dict) -> dict:
        return _handle(request if isinstance(request, dict) else {})

    def main() -> None:
        app.run()

except ImportError:
    # Fallback if SDK not installed: implement /invocations and /ping contract for local test
    def main() -> None:
        import http.server
        import socketserver

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/ping":
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self) -> None:
                if self.path == "/invocations":
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length) if length else b"{}"
                    try:
                        req = json.loads(body.decode("utf-8"))
                        out = _handle(req)
                    except Exception:
                        out = {"result": "Error parsing request"}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(out).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

        with socketserver.TCPServer(("", 8080), Handler) as httpd:
            httpd.serve_forever()


if __name__ == "__main__":
    main()
