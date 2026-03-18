#!/usr/bin/env python3
"""Start local API using RDS IAM auth (not DATABASE_URL). For Phase 4 verification."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

os.environ["DATABASE_URL"] = ""
os.environ.setdefault("RDS_CONFIG_SECRET_NAME", "cdss-dev/rds-config")
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("TUNNEL_LOCAL_PORT", "5433")
os.environ.setdefault("BEDROCK_CONFIG_SECRET_NAME", "cdss-dev/bedrock-config")
os.environ.setdefault("CDSS_REPO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PORT", "8080")

from http.server import HTTPServer

# Prevent run_api_local from loading .env (which has wrong DATABASE_URL)
class FakeDotenv:
    @staticmethod
    def load_dotenv(*a, **kw):
        pass
sys.modules["dotenv"] = FakeDotenv()

# Now import the server handler
import scripts.run_api_local as srv
srv.USE_DB = True

port = int(os.environ.get("PORT", "8080"))
print(f"CDSS local API (IAM auth) at http://localhost:{port}")
print(f"  RDS_CONFIG_SECRET_NAME={os.environ.get('RDS_CONFIG_SECRET_NAME')}")
print(f"  TUNNEL_LOCAL_PORT={os.environ.get('TUNNEL_LOCAL_PORT')}")
print(f"  DATABASE_URL={'(empty)' if not os.environ.get('DATABASE_URL') else 'set'}")
print(flush=True)
httpd = HTTPServer(("", port), srv.CDSSHandler)
httpd.serve_forever()
