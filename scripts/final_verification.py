
import json
import os
import logging
import sys
from datetime import datetime, timezone
from cdss.api.handlers.engagement import handler as engagement_handler
from cdss.db.session import get_session
from cdss.db.models import Visit, Patient, Reminder, Medication
from sqlalchemy import text, delete

# Configure logging to be quiet except for our report
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("verification")

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

def run_verification():
    print("="*60)
    print("CDSS MANUAL VERIFICATION REPORT")
    print("="*60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-"*60)

    # 1. Check DB Schema
    print("[1] Database Schema Migration Check")
    with get_session() as session:
        result = session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'visits' AND column_name = 'extracted_entities';"))
        row = result.fetchone()
        if row:
            print(f"  SUCCESS: column 'extracted_entities' exists (Type: {row[1]})")
        else:
            print("  FAILURE: column 'extracted_entities' NOT found in visits table")
            return

    # 2. Consultation/Summary Flow
    print("\n[2] Consultation Summary & Entity Extraction Check")
    patient_id = "PT-1001"
    transcript = "Patient reports sharp chest pain when breathing deeply. History of asthma. Advice: Rest and follow-up in 2 days. Prescribed Salbutamol inhaler."
    
    # Create Visit
    start_body = {
        "patient_id": patient_id,
        "doctor_id": "DOC-001",
        "notes": transcript
    }
    event = mock_event("POST", "/api/v1/consultations", body=start_body)
    resp = engagement_handler(event, None)
    if resp['statusCode'] != 200:
        print(f"  FAILURE: Create visit failed with {resp['statusCode']}")
        return
    
    visit_id = json.loads(resp['body'])['visitId']
    print(f"  - Visit Created (ID: {visit_id})")

    # Generate Summary
    gen_event = mock_event("POST", f"/api/v1/consultations/{visit_id}/generate-summary")
    gen_resp = engagement_handler(gen_event, None)
    if gen_resp['statusCode'] != 200:
        print(f"  FAILURE: Summary generation failed with {gen_resp['statusCode']}")
        print(f"  Response: {gen_resp['body']}")
        return

    res_body = json.loads(gen_resp['body'])
    print("  SUCCESS: API response received for summary generation")
    print(f"  Summary: {res_body.get('summary')}")
    print(f"  Extracted Entities: {json.dumps(res_body.get('extracted_entities'), indent=4)}")

    # Verify in DB
    with get_session() as session:
        session.expire_all()
        visit = session.get(Visit, visit_id)
        if visit.summary and visit.extracted_entities:
            print("  SUCCESS: Data persisted in database.")
        else:
            print("  FAILURE: Data NOT persisted in database.")

    # 3. Adherence Reporting
    print("\n[3] Adherence Reporting Check (Patient: PT-1001)")
    with get_session() as session:
        # Clear and seed specific adherence data
        session.execute(delete(Reminder).where(Reminder.patient_id == patient_id))
        now = datetime.now(timezone.utc)
        reminders = [
            Reminder(patient_id=patient_id, reminder_at=now, sent_at=now, created_at=now),
            Reminder(patient_id=patient_id, reminder_at=datetime(2000, 1, 1, tzinfo=timezone.utc), sent_at=None, created_at=now),
        ]
        session.add_all(reminders)
        session.flush()

    adh_event = mock_event("GET", "/api/v1/reminders/adherence", params={"patient_id": patient_id})
    adh_resp = engagement_handler(adh_event, None)
    if adh_resp['statusCode'] != 200:
        print(f"  FAILURE: Adherence API failed with {adh_resp['statusCode']}")
        return

    adh_data = json.loads(adh_resp['body'])
    print(f"  SUCCESS: Adherence Data Retrieved")
    print(f"  Total Reminders: {adh_data.get('reminders_total')}")
    print(f"  Sent Reminders: {adh_data.get('reminders_sent')}")
    print(f"  Overdue Reminders: {adh_data.get('reminders_overdue')}")
    print(f"  Adherence Pct: {adh_data.get('adherence_pct')}% (Expected: 50.0%)")

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    # Use Secrets Manager (RDS_CONFIG_SECRET_NAME + AWS_REGION) or set DATABASE_URL for local dev.
    # Never commit credentials. For local runs without AWS, use: export DATABASE_URL=postgresql://...
    if not os.environ.get("DATABASE_URL") and not os.environ.get("RDS_CONFIG_SECRET_NAME"):
        print("Set DATABASE_URL or RDS_CONFIG_SECRET_NAME and AWS_REGION before running.")
        sys.exit(1)
    run_verification()
