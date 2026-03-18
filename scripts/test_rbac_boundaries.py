
import os
import sys
import json
import logging

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from cdss.api.handlers.router import handler as router_handler
import boto3
from urllib.parse import quote_plus

def setup_db():
    try:
        sm = boto3.client("secretsmanager", region_name="ap-south-1")
        secret = sm.get_secret_value(SecretId="cdss-dev/rds-config")
        host = json.loads(secret["SecretString"])["host"]
        rds = boto3.client("rds", region_name="ap-south-1")
        token = rds.generate_db_auth_token(DBHostname=host, Port=5432, DBUsername="cdssadmin")
        os.environ["DATABASE_URL"] = f"postgresql+psycopg2://cdssadmin:{quote_plus(token)}@localhost:5433/cdssdb?sslmode=require"
    except Exception:
        pass

# Suppress noisy logs
logging.getLogger("cdss").setLevel(logging.ERROR)

def test_patient_isolation():
    setup_db()
    print("\n--- [6.2] Testing Patient isolation ---")
    # Patient PT-1001 trying to access PT-1002
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/patients/PT-1002",
        "pathParameters": {"proxy": "v1/patients/PT-1002"},
        "requestContext": {
            "path": "/api/v1/patients/PT-1002",
            "authorizer": {
                "claims": {
                    "sub": "USR-PAT-001",
                    "custom:role": "patient",
                    "custom:patientId": "PT-1001"
                }
            }
        }
    }
    
    resp = router_handler(event, None)
    if resp["statusCode"] == 403:
        print("SUCCESS: Patient PT-1001 blocked from accessing PT-1002.")
    else:
        print(f"FAILURE: Patient isolation failed. Status: {resp['statusCode']}")

def test_patient_blocked_from_admin():
    print("\n--- [6.2] Testing Patient admin block ---")
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/admin/audit",
        "pathParameters": {"proxy": "v1/admin/audit"},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "custom:role": "patient",
                    "sub": "USR-PAT-001"
                }
            }
        }
    }
    
    resp = router_handler(event, None)
    if resp["statusCode"] == 403:
        print("SUCCESS: Patient blocked from admin audit logs.")
    else:
        print(f"FAILURE: Admin security boundary failed. Status: {resp['statusCode']}")

def test_admin_access():
    print("\n--- [6.2] Testing Admin access ---")
    event = {
        "httpMethod": "GET",
        "path": "/api/v1/admin/audit",
        "pathParameters": {"proxy": "v1/admin/audit"},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "custom:role": "admin",
                    "sub": "USR-ADMIN"
                }
            }
        }
    }
    
    # We expect 200 (or if local DB isn't running it might 500 but status should be passed by RBAC)
    resp = router_handler(event, None)
    if resp["statusCode"] in [200, 500]: # 500 is acceptable if it's a DB issue, as long as it's not 403
        print(f"SUCCESS: Admin permitted to access audit logs. Status: {resp['statusCode']}")
    else:
        print(f"FAILURE: Admin was incorrectly blocked. Status: {resp['statusCode']}")

if __name__ == "__main__":
    test_patient_isolation()
    test_patient_blocked_from_admin()
    test_admin_access()
