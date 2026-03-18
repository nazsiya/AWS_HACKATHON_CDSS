
import os
import sys
import json
import boto3
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from cdss.db.session import get_session
from cdss.db.models import Surgery, Patient, Medication, AlertLog, EscalationLog
from cdss.services.alerts import check_vital_thresholds
from cdss.services.drug_interactions import check_drug_interactions

def setup_db():
    try:
        sm = boto3.client("secretsmanager", region_name="ap-south-1")
        secret = sm.get_secret_value(SecretId="cdss-dev/rds-config")
        host = json.loads(secret["SecretString"])["host"]
        rds = boto3.client("rds", region_name="ap-south-1")
        token = rds.generate_db_auth_token(DBHostname=host, Port=5432, DBUsername="cdssadmin")
        os.environ["DATABASE_URL"] = f"postgresql+psycopg2://cdssadmin:{quote_plus(token)}@localhost:5433/cdssdb?sslmode=require"
        return True
    except Exception as e:
        print(f"DB Setup failed: {e}")
        return False

def test_surgery_scheduling_path():
    print("\n--- [6.1] Testing Surgery Scheduling Path ---")
    patient_id = "PT-1005" # Existing patient from seed
    surgery_id = f"SRG-TEST-{uuid.uuid4().hex[:6]}"
    
    with get_session() as session:
        # Create a new surgery
        surg = Surgery(
            id=surgery_id,
            patient_id=patient_id,
            type="Orthopedic Surgery",
            status="scheduled",
            scheduled_date=(datetime.now(timezone.utc) + timedelta(days=5)).date(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(surg)
        session.flush()
        
        # Verify it exists
        fetched = session.get(Surgery, surgery_id)
        if fetched:
            print(f"SUCCESS: Surgery {surgery_id} scheduled for patient {patient_id}")
            session.delete(fetched)
            session.commit()
            print("VERIFIED: Surgery record state transition and cleanup successful.")
        else:
            print(f"FAILURE: Surgery {surgery_id} not found after creation.")

def test_emergency_alert_integrity():
    print("\n--- [6.1] Testing Emergency Alert Integrity ---")
    patient_id = "PT-1001"
    vitals = {"heart_rate": 145} # Triggers Tachycardia
    
    result = check_vital_thresholds(patient_id, vitals)
    if result and result.get("success"):
        alert_id = result.get("alert_id")
        print(f"SUCCESS: Critical alert emitted: {alert_id}")
        
        with get_session() as session:
            from sqlalchemy import select
            alert = session.scalar(select(AlertLog).where(AlertLog.alert_id == alert_id))
            esc = session.scalar(select(EscalationLog).where(EscalationLog.alert_id == alert_id))
            
            if alert and esc:
                print(f"VERIFIED: AlertLog and EscalationLog linked. Target Channel: {esc.channel}")
            else:
                print("FAILURE: database linkage check failed for emergency alert.")
    else:
        print("FAILURE: Emergency alert trigger failed.")

def test_drug_interaction_safety():
    print("\n--- [6.1] Testing Drug Interaction Safety ---")
    # Patient PT-1002 has Warfarin (previously seeded or added)
    patient_id = "PT-1002"
    
    # Check for Metformin (High Interaction with some meds, let's try a known one)
    # The drug_interactions service has a static map for demonstration
    result = check_drug_interactions(patient_id, "Aspirin")
    if result.get("interactions"):
         print(f"SUCCESS: {len(result['interactions'])} interaction(s) found for patient {patient_id}.")
         print(f"VERIFIED: Warning: {result['interactions'][0]['warning']}")
    else:
        print(f"FAILURE: No interactions found for critical pair.")

if __name__ == "__main__":
    if setup_db():
        test_surgery_scheduling_path()
        test_emergency_alert_integrity()
        test_drug_interaction_safety()
    else:
        sys.exit(1)
