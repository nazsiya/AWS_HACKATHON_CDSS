
import os
import sys
import json
import boto3
from datetime import datetime, timezone
from urllib.parse import quote_plus

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from cdss.db.session import get_session
from cdss.db.models import AlertLog, EscalationLog, Patient, Medication
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

def test_vital_alerts():
    print("\n--- Testing Vital Alerts ---")
    patient_id = "PT-1001"
    critical_vitals = {"heart_rate": 155, "blood_pressure_sys": 200, "oxygen_saturation": 88}
    
    result = check_vital_thresholds(patient_id, critical_vitals)
    if result and result.get("success"):
        alert_id = result.get("alert_id")
        print(f"SUCCESS: Alert emitted! AlertID: {alert_id}")
        
        # Verify in DB
        with get_session() as session:
            from sqlalchemy import select
            alert = session.scalar(select(AlertLog).where(AlertLog.alert_id == alert_id))
            if alert:
                print(f"VERIFIED: AlertLog entry found in DB. Severity: {alert.severity}")
            
            esc = session.scalar(select(EscalationLog).where(EscalationLog.alert_id == alert_id))
            if esc:
                print(f"VERIFIED: EscalationLog entry found. Level: {esc.level}, Channel: {esc.channel}")
            else:
                print("FAILURE: EscalationLog not found for critical alert.")
    else:
        print("FAILURE: No alert emitted for critical vitals.")

def test_drug_interactions():
    print("\n--- Testing Drug Interactions ---")
    patient_id = "PT-1002"
    
    # Pre-seed patient with Warfarin if not there (or assume it's in seed)
    with get_session() as session:
        # Check if patient exists
        p = session.get(Patient, patient_id)
        if not p:
            p = Patient(id=patient_id, name="Test Patient", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
            session.add(p)
            session.flush()
            
        # Add Warfarin
        m = Medication(patient_id=patient_id, medication_name="Warfarin", status="active", created_at=datetime.now(timezone.utc))
        session.add(m)
        session.commit()

    # Now check for Aspirin interaction
    result = check_drug_interactions(patient_id, "Aspirin")
    interactions = result.get("interactions", [])
    if interactions:
        print(f"SUCCESS: {len(interactions)} interaction(s) detected.")
        for i in interactions:
            print(f"  - {i['warning']}")
        
        alert_ids = result.get("alert_ids", [])
        if alert_ids:
            print(f"SUCCESS: Alert IDs generated: {alert_ids}")
            with get_session() as session:
                from sqlalchemy import select
                for aid in alert_ids:
                    alert = session.scalar(select(AlertLog).where(AlertLog.alert_id == aid))
                    if alert:
                        print(f"VERIFIED: AlertLog {aid} found in DB.")
        else:
            print("FAILURE: No alert IDs generated for interaction.")
    else:
        print("FAILURE: Interaction not detected for Warfarin + Aspirin.")

if __name__ == "__main__":
    if setup_db():
        test_vital_alerts()
        test_drug_interactions()
    else:
        sys.exit(1)
