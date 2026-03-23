import os
import psycopg2
import random
from datetime import date, timedelta

def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    pwd = os.environ.get("CDSS_DB_PASSWORD")
    if not pwd:
        raise RuntimeError("Set DATABASE_URL or CDSS_DB_PASSWORD (do not commit credentials).")
    return psycopg2.connect(
        host="localhost",
        database="cdssdb",
        user="postgres",
        password=pwd,
        port="5433"
    )

def generate_patient(i):
    first_names = ["Arun", "Sanjay", "Deepak", "Amit", "Rahul", "Neha", "Kavita", "Anjali", "Sneha", "Pooja", "Vikram", "Aditya", "Rohan", "Ishaan", "Zain", "Sara", "Myra", "Kiara", "Aavya", "Anvi"]
    last_names = ["Sharma", "Verma", "Gupta", "Malhotra", "Kapoor", "Khan", "Patel", "Reddy", "Nair", "Iyer", "Joshi", "Singh", "Chopra", "Das", "Bose", "Rao", "Mishra", "Pandey", "Yadav", "Tiwari"]
    genders = ["Male", "Female"]
    blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    severities = ["low", "moderate", "high", "critical"]
    statuses = ["waiting", "in-consultation", "scheduled", "admitted", "discharged"]
    
    full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    dob = date(1950, 1, 1) + timedelta(days=random.randint(0, 25000))
    gender = random.choice(genders)
    blood_group = random.choice(blood_groups)
    severity = random.choice(severities)
    status = random.choice(statuses)
    patient_id = f"PT-{1006 + i}"
    abdm_id = f"ABDM-2024-{100 + i}"
    
    return (patient_id, abdm_id, full_name, dob, gender, blood_group, f"+91 {random.randint(60000, 99999)} {random.randint(10000, 99999)}", severity, status)

def generate_doctor(i):
    first_names = ["Dr. Rajesh", "Dr. Sunita", "Dr. Anil", "Dr. Geeta", "Dr. Manoj"]
    last_names = ["Kulkarni", "Deshmukh", "Patil", "Pawar", "Shinde"]
    specializations = ["Dermatology", "Neurology", "Pediatrics", "Psychiatry", "ENT"]
    departments = ["General", "Cognitive Sciences", "Maternal & Child", "Mental Health", "Specialized Surgery"]
    
    full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    spec = random.choice(specializations)
    dept = random.choice(departments)
    doctor_id = f"DR-{1005 + i}"
    email = f"{full_name.lower().replace(' ', '.').replace('dr.', '')}@hospital.com"
    
    return (doctor_id, full_name, spec, dept, email, f"+91 {random.randint(60000, 99999)} {random.randint(10000, 99999)}")

def _row_exists(cur, table: str, pk_col: str, pk_val) -> bool:
    cur.execute(f"SELECT 1 FROM {table} WHERE {pk_col} = %s LIMIT 1", (pk_val,))
    return cur.fetchone() is not None


def expand_db():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Adding up to 5 more doctors (skips rows that already exist)...")
    doctors_added = 0
    for i in range(5):
        doc = generate_doctor(i)
        if _row_exists(cur, "doctors", "doctor_id", doc[0]):
            continue
        cur.execute(
            "INSERT INTO doctors (doctor_id, full_name, specialization, department, email, phone_number) VALUES (%s, %s, %s, %s, %s, %s)",
            doc,
        )
        doctors_added += 1

    print("Adding up to 20 more patients with vitals (skips rows that already exist)...")
    patients_added = 0
    for i in range(20):
        pat = generate_patient(i)
        if _row_exists(cur, "patients", "patient_id", pat[0]):
            continue
        cur.execute(
            "INSERT INTO patients (patient_id, abdm_id, full_name, date_of_birth, gender, blood_group, phone_number, severity_level, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            pat,
        )
        cur.execute(
            "INSERT INTO vitals_history (patient_id, heart_rate, bp_systolic, bp_diastolic, spo2_percent, temperature_f) VALUES (%s, %s, %s, %s, %s, %s)",
            (pat[0], random.randint(60, 100), random.randint(110, 140), random.randint(70, 90), random.randint(94, 100), random.uniform(97.0, 99.5)),
        )
        patients_added += 1

    print(f"Done: {doctors_added} doctors inserted, {patients_added} patients inserted.")

    conn.commit()
    cur.close()
    conn.close()
    print("Expansion complete!")

if __name__ == "__main__":
    expand_db()
