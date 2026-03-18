
import os
import sys
from pathlib import Path

# Add src to path
root = Path(__file__).resolve().parent.parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from cdss.db.session import get_session
from cdss.db.models import (
    Patient, Surgery, Hospital, Resource, Visit, Medication, Reminder, Consent, AuditLog,
    User, Doctor, MedicalCondition, Allergy, SurgeryRequirement, SurgicalTeamMember,
    ResourceStatusLog, DoctorReplacement, Conversation, ConversationSummary,
    MedicationAdherenceLog, LanguageTranslation, AgentEvent, Notification
)

def check_counts():
    print("Checking Aurora database counts...")
    try:
        import boto3, json
        from urllib.parse import quote_plus
        host = json.loads(boto3.client('secretsmanager', region_name='ap-south-1').get_secret_value(SecretId='cdss-dev/rds-config')['SecretString'])['host']
        token = boto3.client('rds', region_name='ap-south-1').generate_db_auth_token(DBHostname=host, Port=5432, DBUsername='cdssadmin')
        os.environ['DATABASE_URL'] = f'postgresql+psycopg2://cdssadmin:{quote_plus(token)}@localhost:5433/cdssdb?sslmode=require'
    except Exception as e:
        print(f"Failed to generate IAM token: {e}")

    try:
        with get_session() as session:
            # Using count() on query is fine for small seeds
            counts = {
                "Users": session.query(User).count(),
                "Doctors": session.query(Doctor).count(),
                "Patients": session.query(Patient).count(),
                "Hospitals": session.query(Hospital).count(),
                "Surgeries": session.query(Surgery).count(),
                "Visits": session.query(Visit).count(),
                "Resources": session.query(Resource).count(),
                "Medications": session.query(Medication).count(),
                "Reminders": session.query(Reminder).count(),
                "Conditions": session.query(MedicalCondition).count(),
                "Allergies": session.query(Allergy).count(),
                "SurgeryReqs": session.query(SurgeryRequirement).count(),
                "Conversations": session.query(Conversation).count(),
                "Notifications": session.query(Notification).count(),
                "AgentEvents": session.query(AgentEvent).count(),
            }
            print("Connection Successful!")
            for entity, count in counts.items():
                print(f"{entity}: {count}")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_counts()
