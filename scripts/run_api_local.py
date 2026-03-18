#!/usr/bin/env python3
"""
Local HTTP server that wraps the CDSS Lambda router for frontend-to-backend testing.

Run from repo root:
  PYTHONPATH=src python scripts/run_api_local.py

Optional: create .env in repo root with DATABASE_URL=postgresql://... to use a real
database; otherwise the server uses in-memory mock data for patients and surgeries.

Frontend: In frontend/apps/doctor-dashboard set .env.local:
  VITE_API_URL=http://localhost:8080
  VITE_USE_MOCK=false

Then run: npm run dev. The app will call this server.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import contextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

# Configure logging for local visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("run_api_local")

# Load .env from repo root so DATABASE_URL / RDS_CONFIG_SECRET_NAME are set when present
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# So router can serve /docs/swagger.yaml when cwd differs
os.environ.setdefault("CDSS_REPO_ROOT", str(REPO_ROOT))

# Optional: load config.json for local run (align with PROJECT_REFERENCE / all-secrets)
_config_path = REPO_ROOT / "config.json"
if _config_path.exists():
    try:
        _cfg = json.loads(_config_path.read_text(encoding="utf-8"))
        if not os.environ.get("AWS_REGION") and _cfg.get("aws_region"):
            os.environ["AWS_REGION"] = _cfg["aws_region"]
        if not os.environ.get("BEDROCK_CONFIG_SECRET_NAME") and _cfg.get("bedrock_config_secret_name"):
            os.environ["BEDROCK_CONFIG_SECRET_NAME"] = _cfg["bedrock_config_secret_name"]
        if not os.environ.get("CDSS_APP_CONFIG_SECRET_NAME") and _cfg.get("app_config_secret_name"):
            os.environ["CDSS_APP_CONFIG_SECRET_NAME"] = _cfg["app_config_secret_name"]
        if not os.environ.get("RDS_CONFIG_SECRET_NAME") and _cfg.get("rds_config_secret_name"):
            os.environ["RDS_CONFIG_SECRET_NAME"] = _cfg["rds_config_secret_name"]
        # MCP / ABDM endpoints (Phase 2): set from config so adapter can call real or sandbox when non-empty
        if _cfg.get("mcp_hospital_endpoint") and not os.environ.get("MCP_HOSPITAL_ENDPOINT"):
            os.environ["MCP_HOSPITAL_ENDPOINT"] = str(_cfg["mcp_hospital_endpoint"]).strip()
        if _cfg.get("mcp_abdm_endpoint") and not os.environ.get("MCP_ABDM_ENDPOINT"):
            os.environ["MCP_ABDM_ENDPOINT"] = str(_cfg["mcp_abdm_endpoint"]).strip()
        if _cfg.get("abdm_sandbox_url") and not os.environ.get("ABDM_SANDBOX_URL"):
            os.environ["ABDM_SANDBOX_URL"] = str(_cfg["abdm_sandbox_url"]).strip()
    except Exception:
        pass

# Optional: mock DB when no DATABASE_URL so server works without Aurora
USE_DB = bool(os.environ.get("DATABASE_URL") or os.environ.get("RDS_CONFIG_SECRET_NAME"))


def _mock_session():
    import datetime
    from unittest.mock import MagicMock

    class MockModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Sample Patients
    patients = [
        MockModel(id="PT-1001", name="Rajesh Kumar", date_of_birth=datetime.date(1980, 5, 20), gender="M", conditions=["Hypertension"], blood_group="B+", severity="moderate", status="active", vitals={"bp": "130/82", "hr": 78}, last_visit=datetime.date(2025, 2, 20)),
        MockModel(id="PT-1002", name="Priya Sharma", date_of_birth=datetime.date(1992, 8, 15), gender="F", conditions=["Asthma"], blood_group="O+", severity="low", status="active", vitals={"bp": "118/76", "hr": 72}, last_visit=datetime.date(2025, 3, 1)),
    ]

    # Sample Surgeries (include ot_id, surgeon_id, duration_minutes for list/detail handlers)
    surgeries = [
        MockModel(id="SRG-001", patient_id="PT-1001", type="Laparoscopic Cholecystectomy", scheduled_date=datetime.date(2025, 3, 15), scheduled_time="09:00", status="scheduled", requirements={"instruments": ["Laparoscope"], "complexity": "Moderate"}, ot_id="OT-1", surgeon_id="DR-001", duration_minutes=90),
        MockModel(id="SRG-002", patient_id="PT-1003", type="Cataract Surgery", scheduled_date=datetime.date(2025, 3, 18), scheduled_time="11:00", status="scheduled", requirements={"instruments": ["IOL"], "complexity": "Low"}, ot_id="OT-2", surgeon_id="DR-002", duration_minutes=45),
    ]

    session = MagicMock()
    
    # Mocking session.scalars(select(...)).all()
    def mock_scalars(statement):
        stmt_str = str(statement).lower()
        mock_result = MagicMock()
        if "from patients" in stmt_str:
            mock_result.all.return_value = patients
            mock_result.__iter__ = lambda x: iter(patients)
        elif "from surgeries" in stmt_str:
            mock_result.all.return_value = surgeries
            mock_result.__iter__ = lambda x: iter(surgeries)
        else:
            mock_result.all.return_value = []
            mock_result.__iter__ = lambda x: iter([])
        return mock_result

    session.scalars.side_effect = mock_scalars
    
    def mock_scalar(statement):
        stmt_str = str(statement).lower()
        if "from patients" in stmt_str:
            return patients[0]
        return None
        
    session.scalar.side_effect = mock_scalar

    # Surgery list/detail use session.execute(select(Surgery, Patient.name).join(...)).all() / .first()
    patient_names = {"PT-1001": "Rajesh Kumar", "PT-1003": "Unknown"}
    surgery_rows = [(s, patient_names.get(s.patient_id, "Unknown")) for s in surgeries]

    def mock_execute(statement):
        stmt_str = str(statement).lower()
        mock_result = MagicMock()
        if "surgeries" in stmt_str and ("join" in stmt_str or "patient" in stmt_str):
            mock_result.all.return_value = surgery_rows
            mock_result.first.return_value = surgery_rows[0] if surgery_rows else None
            mock_result.__iter__ = lambda x: iter(surgery_rows)
        else:
            mock_result.all.return_value = []
            mock_result.first.return_value = None
            mock_result.__iter__ = lambda x: iter([])
        return mock_result

    session.execute.side_effect = mock_execute

    def mock_get(model_class, ident):
        if str(model_class).lower().endswith("patient'>"):
            for p in patients:
                if p.id == ident:
                    return p
        return None
    session.get.side_effect = mock_get

    return session


@contextmanager
def _mock_get_session():
    mock_sess = _mock_session()

    @contextmanager
    def fake_cm():
        yield mock_sess

    def fake_get_session(secret_name=None):
        return fake_cm()

    # Patch both the session module and handlers that supervisor imports (they hold a
    # reference to get_session at import time, so patch where they look it up).
    with patch("cdss.db.session.get_session", fake_get_session), \
         patch("cdss.api.handlers.patient.get_session", fake_get_session), \
         patch("cdss.api.handlers.surgery.get_session", fake_get_session), \
         patch("cdss.api.handlers.resource.get_session", fake_get_session), \
         patch("cdss.api.handlers.scheduling.get_session", fake_get_session), \
         patch("cdss.api.handlers.engagement.get_session", fake_get_session):
        yield


class CDSSHandler(BaseHTTPRequestHandler):
    def _build_event(self, path: str, method: str, body_bytes: bytes | None) -> dict:
        path = path or "/"
        query = ""
        if "?" in path:
            path, query = path.split("?", 1)
        
        if path.startswith("/api/"):
            proxy = path[5:].rstrip("/")  # strip /api/
            path_params = {"proxy": proxy}
        else:
            path_params = None
            
        # Parse query params
        q_params = {}
        if query:
            import urllib.parse
            q_params = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}

        role = self.headers.get("X-CDSS-Role", "doctor")
        accept_lang = self.headers.get("Accept-Language", "en")

        event = {
            "httpMethod": method,
            "path": path,
            "pathParameters": path_params,
            "headers": {
                "Accept-Language": accept_lang,
                "Content-Type": self.headers.get("Content-Type", "application/json"),
            },
            "requestContext": {
                "path": path, 
                "authorizer": {
                    "claims": {
                        "custom:role": role, 
                        "sub": "local", 
                        "email": "local@test",
                        "name": "Local Test User"
                    }
                }
            },
            "body": body_bytes.decode("utf-8") if body_bytes else None,
            "queryStringParameters": q_params if q_params else None,
        }
        if self.headers.get("Authorization"):
            event["requestContext"]["authorizer"]["claims"]["token"] = self.headers["Authorization"]
        return event

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        self._handle_request("GET", None)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        self._handle_request("POST", body)

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        self._handle_request("PUT", body)

    def _handle_request(self, method: str, body: bytes | None):
        path = self.path
        event = self._build_event(path, method, body)
        try:

            if USE_DB:
                from cdss.api.handlers.router import handler
                result = handler(event, None)
            else:
                with _mock_get_session():
                    from cdss.api.handlers.router import handler
                    result = handler(event, None)
        except Exception as e:
            result = {"statusCode": 500, "headers": {}, "body": json.dumps({"error": str(e)})}
        status = result.get("statusCode", 500)
        headers = result.get("headers", {})
        body_out = result.get("body", "{}")
        # Conform to api-aws: API Gateway proxy format (statusCode, body, headers, Content-Type: application/json)
        self.send_response(status)
        self._send_cors()
        for k, v in headers.items():
            # Skip CORS headers already set by _send_cors to avoid duplicates
            # (browsers reject duplicate Access-Control-Allow-Origin values)
            if k.lower().startswith("access-control-"):
                continue
            self.send_header(k, v)
        self.end_headers()
        if body_out:
            self.wfile.write(body_out.encode("utf-8") if isinstance(body_out, str) else body_out)

    def log_message(self, format, *args):
        print(f"[CDSS] {args[0]}")


def main():
    port = int(os.environ.get("PORT", "8080"))
    with HTTPServer(("", port), CDSSHandler) as httpd:
        db_source = "database (DATABASE_URL/RDS)" if USE_DB else "mock data (set DATABASE_URL in .env for real DB)"
        print(f"CDSS local API at http://localhost:{port}")
        print(f"Data source: {db_source}")
        print("Set VITE_API_URL=http://localhost:{port} and VITE_USE_MOCK=false in frontend .env.local")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
