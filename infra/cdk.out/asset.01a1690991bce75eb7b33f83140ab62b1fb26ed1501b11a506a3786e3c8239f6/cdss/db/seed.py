"""
Seed CDSS RDS with comprehensive sample data for development and testing.
Includes 5 doctors and 25 patients with diverse clinical data.
Usage: python -m cdss.db.seed [--force]
"""

import argparse
import sys
import random
from datetime import date, datetime, timedelta, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> date:
    return (datetime.now(timezone.utc) - timedelta(days=n)).date()


def _hours_from_now(n: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=n)


def run_seed(force: bool = False) -> int:
    from cdss.db.session import get_session
    from cdss.db.models import (
        User, Doctor, Patient, Hospital, Visit, Surgery, Resource,
        ScheduleSlot, Medication, Reminder, Consent, AuditLog,
        MedicalCondition, Allergy, SurgeryRequirement, SurgicalTeamMember,
        ResourceStatusLog, DoctorReplacement, Conversation,
        ConversationSummary, MedicationAdherenceLog, LanguageTranslation,
        AgentEvent, Notification
    )

    with get_session() as session:
        from sqlalchemy import func, select, delete

        # Check for existing data
        existing = session.scalar(select(func.count(Patient.id)))
        if existing and existing > 0 and not force:
            print("Seed data already present (patients exist). Use --force to replace.")
            return 0

        if force:
            print("Clearing existing seed data...")
            for model in [
                AgentEvent, Notification, LanguageTranslation, MedicationAdherenceLog,
                Reminder, Medication, ConversationSummary, Conversation,
                DoctorReplacement, ScheduleSlot, ResourceStatusLog, SurgeryRequirement,
                SurgicalTeamMember, Surgery, Visit, Allergy, MedicalCondition,
                Consent, Patient, Doctor, User, Hospital, Resource, AuditLog
            ]:
                session.execute(delete(model))
            session.flush()

        # ─── Hospitals ────────────────────────────────────────────────
        hospitals_data = [
            {"id": "HOSP-001", "name": "AIIMS Delhi", "city": "New Delhi", "state": "Delhi", "specialties": ["Cardiology", "Neurology", "Oncology", "Orthopedics"], "tier": "tertiary", "status": "active"},
            {"id": "HOSP-002", "name": "Apollo Mumbai", "city": "Mumbai", "state": "Maharashtra", "specialties": ["Oncology", "Orthopedics", "Cardiology"], "tier": "tertiary", "status": "active"},
            {"id": "HOSP-003", "name": "Fortis Bangalore", "city": "Bangalore", "state": "Karnataka", "specialties": ["Neurology", "Gastroenterology"], "tier": "tertiary", "status": "active"},
        ]
        for h in hospitals_data:
            session.add(Hospital(**h))
        session.flush()

        # ─── Users & Doctors (5 Doctors) ──────────────────────────────
        specs = ["Cardiology", "Neurology", "Oncology", "Orthopedics", "General Surgery"]
        doctor_names = ["Dr. Rajesh Kumar", "Dr. Meera Singh", "Dr. Amit Verma", "Dr. Sneha Rao", "Dr. Vikram Seth"]
        
        for i in range(1, 6):
            doc_id = f"DOC-{i:03d}"
            usr_id = f"USR-DOC-{i:03d}"
            email = f"doc{i}@cdss.ai"
            
            session.add(User(user_id=usr_id, email=email, role="doctor"))
            session.flush()
            
            session.add(Doctor(
                doctor_id=doc_id,
                user_id=usr_id,
                full_name=doctor_names[i-1],
                specialization=specs[i-1],
                hospital_id="HOSP-001" if i <= 3 else "HOSP-002",
                status="available" if i % 2 == 1 else "busy"
            ))
        session.flush()

        # ─── Patients (25 Patients) ───────────────────────────────────
        genders = ["M", "F"]
        blood_groups = ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"]
        patient_names = [
            "Amit Shah", "Priya Das", "Rohan Gupta", "Anjali Nair", "Vikram Joshi",
            "Sonal Mehta", "Rahul Sharma", "Kavita Reddy", "Arjun Patel", "Deepa Iyer",
            "Manish Pandey", "Nisha Saxena", "Varun Chawla", "Pooja Malhotra", "Suresh Yadav",
            "Meera Pillai", "Harish Menon", "Sunita Devi", "Rajesh Khanna", "Lata Mangeshkar",
            "Sachin Tendulkar", "Virat Kohli", "Saina Nehwal", "Abhinav Bindra", "Mary Kom"
        ]

        for i in range(1, 26):
            pt_id = f"PT-{1000 + i}"
            usr_id = f"USR-PAT-{i:03d}" if i <= 10 else None # Only first 10 have user accounts
            
            if usr_id:
                session.add(User(user_id=usr_id, email=f"patient{i}@example.com", role="patient"))
                session.flush()
            
            p = Patient(
                id=pt_id,
                user_id=usr_id,
                name=patient_names[i-1],
                date_of_birth=date(1960 + random.randint(0, 50), random.randint(1, 12), random.randint(1, 28)),
                gender=random.choice(genders),
                blood_group=random.choice(blood_groups),
                ward="Ward A" if i <= 10 else ("Ward B" if i <= 20 else "ICU"),
                severity="moderate" if i % 3 == 0 else ("high" if i % 5 == 0 else "low"),
                status="active" if i < 24 else "discharged",
                vitals={"bp": f"{110 + random.randint(0, 40)}/{70 + random.randint(0, 20)}", "hr": 60 + random.randint(0, 40)},
                created_at=_now(),
                updated_at=_now()
            )
            session.add(p)
            session.flush()

            # Add sample conditions and allergies for some patients
            if i % 2 == 0:
                session.add(MedicalCondition(patient_id=pt_id, condition_name="Hypertension", diagnosis_date=_days_ago(365), status="active"))
            if i % 5 == 0:
                session.add(Allergy(patient_id=pt_id, allergen="Penicillin", severity="high"))

        # ─── Visits, Surgeries, and more ──────────────────────────────
        # Generate some visits
        for i in range(1, 11):
            session.add(Visit(
                patient_id=f"PT-{1000 + i}",
                doctor_id=f"DOC-00{1 + (i % 5)}",
                visit_date=_days_ago(random.randint(1, 30)),
                notes=f"Routine checkup for patient {i}",
                created_at=_now()
            ))
        
        # Generate some surgeries
        for i in range(1, 6):
            surg_id = f"SRG-200{i}"
            session.add(Surgery(
                id=surg_id,
                patient_id=f"PT-{1005 + i}",
                surgeon_id=f"DOC-00{1 + (i % 5)}",
                type="General Surgery" if i % 2 == 0 else "Orthopedic Surgery",
                ot_id="OT-1",
                scheduled_date=_days_ago(-i),
                status="scheduled",
                created_at=_now(),
                updated_at=_now()
            ))
            session.flush()
            session.add(SurgicalTeamMember(surgery_id=surg_id, doctor_id=f"DOC-00{1 + (i % 5)}", role="surgeon"))

        # Add Resources
        session.add(Resource(id="OT-1", type="ot", name="Operating Theater 1", status="available", availability={"floor": 3}))
        session.add(Resource(id="VENT-01", type="equipment", name="Ventilator 01", status="available", availability={"location": "ICU"}))

        # Add Notifications
        session.add(Notification(id="NOTIF-001", user_id="USR-DOC-001", message="New patient assigned: PT-1001", severity="INFO", created_at=_now()))

        print(f"Expanded Seed complete: 3 Hospitals, 5 Doctors, 25 Patients, and associated clinical data.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed CDSS RDS with expanded sample data (5 docs, 25 patients)")
    parser.add_argument("--force", action="store_true", help="Clear existing seed data and re-insert")
    args = parser.parse_args()
    try:
        return run_seed(force=args.force)
    except Exception as e:
        print("Seed failed:", e, file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
