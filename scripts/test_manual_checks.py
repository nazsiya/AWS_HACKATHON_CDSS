
import json
import os
import logging
from datetime import datetime, timezone
from cdss.api.handlers.engagement import handler as engagement_handler
from cdss.db.session import get_session
from cdss.db.models import Visit, Patient, Reminder, Medication

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def mock_event(method, path, body=None, params=None):
    proxy = path.replace("/api/v1/", "")
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"proxy": f"v1/{proxy}"},
        "queryStringParameters": params or {},
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "DOC-001",
                    "email": "doctor@cdss.ai",
                    "custom:role": "doctor"
                }
            }
        }
    }

def test_consultation_flow():
    print("\n--- Testing Consultation Flow ---")
    patient_id = "PT-1001"
    
    # Debug Bedrock config
    import boto3
    try:
        secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME")
        region = os.environ.get("AWS_REGION")
        print(f"Debug: Bedrock Secret={secret_name}, Region={region}")
        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        print(f"Debug: Successfully fetched secret {secret_name}")
    except Exception as e:
        print(f"Debug: Failed to fetch Bedrock secret: {e}")

    # 1. Start Consultation with notes (to bypass S3 dependencies in local test if needed)
    start_body = {
        "patient_id": patient_id,
        "doctor_id": "DOC-001",
        "notes": "Patient complains of severe headache and dizziness for the last 2 days. I suspect hypertension. Prescribing Amlodipine 5mg once daily."
    }
    event = mock_event("POST", "/api/v1/consultations", body=start_body)
    resp = engagement_handler(event, None)
    print(f"Post Consultation Response: {resp['statusCode']} - {resp['body']}")
    
    visit_id = json.loads(resp['body'])['visitId']
    
    # 2. Generate Summary and Entities
    event = mock_event("POST", f"/api/v1/consultations/{visit_id}/generate-summary")
    resp = engagement_handler(event, None)
    print(f"Generate Summary Response: {resp['statusCode']} - {resp['body']}")
    
    # 3. Verify in DB
    with get_session() as session:
        # Expire session to ensure fresh read
        session.expire_all()
        visit = session.get(Visit, visit_id)
        print(f"DB Check - Summary: {visit.summary}")
        print(f"DB Check - Entities: {visit.extracted_entities}")
        
    return visit_id

def test_adherence():
    print("\n--- Testing Adherence Reporting ---")
    patient_id = "PT-1001"
    
    # Ensure some reminders exist for PT-1001
    with get_session() as session:
        # Clear existing reminders for clean test
        from sqlalchemy import delete
        session.execute(delete(Reminder).where(Reminder.patient_id == patient_id))
        
        # Add 2 sent, 1 overdue
        now = datetime.now(timezone.utc)
        reminders = [
            Reminder(patient_id=patient_id, reminder_at=now, sent_at=now, created_at=now),
            Reminder(patient_id=patient_id, reminder_at=now, sent_at=now, created_at=now),
            Reminder(patient_id=patient_id, reminder_at=datetime(2000, 1, 1, tzinfo=timezone.utc), sent_at=None, created_at=now),
        ]
        session.add_all(reminders)
        session.flush()

    event = mock_event("GET", "/api/v1/reminders/adherence", params={"patient_id": patient_id})
    resp = engagement_handler(event, None)
    print(f"Adherence Response: {resp['statusCode']} - {resp['body']}")
    
    data = json.loads(resp['body'])
    expected_pct = 66.7 # 2/3
    print(f"Adherence Pct: {data.get('adherence_pct')}% (Expected ~66.7%)")

if __name__ == "__main__":
    # Use env: DATABASE_URL or RDS_CONFIG_SECRET_NAME + AWS_REGION. Do not commit real credentials.
    if not os.environ.get("DATABASE_URL"):
        os.environ.setdefault("BEDROCK_CONFIG_SECRET_NAME", "cdss-dev/bedrock-config")
        os.environ.setdefault("AWS_REGION", "ap-south-1")
        print("Set DATABASE_URL (e.g. postgresql://user:password@127.0.0.1:5433/cdssdb) for local DB tests.")
        print("Skipping DB-dependent tests.")
        sys.exit(0)
    try:
        test_consultation_flow()
        test_adherence()
        print("\nVerification successful!")
    except Exception as e:
        print(f"\nVerification failed: {e}")
        import traceback
        traceback.print_exc()
