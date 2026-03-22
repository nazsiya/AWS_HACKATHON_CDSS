-- CDSS Aurora PostgreSQL initial schema (001).
-- Aligns with src/cdss/db/models.py. Run with: python -m cdss.db.migrations.run

CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(64) PRIMARY KEY,
    abha_id VARCHAR(128),
    name VARCHAR(256) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(32),
    language VARCHAR(16),
    address_json JSONB,
    emergency_contact_json JSONB,
    conditions JSONB,
    allergies JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    last_visit TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_patients_abha_id ON patients(abha_id);

CREATE TABLE IF NOT EXISTS visits (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id VARCHAR(64) NOT NULL,
    visit_date DATE NOT NULL,
    notes TEXT,
    summary TEXT,
    transcript_s3_key VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_visits_patient_id ON visits(patient_id);
CREATE INDEX IF NOT EXISTS ix_visits_doctor_id ON visits(doctor_id);

CREATE TABLE IF NOT EXISTS surgeries (
    id VARCHAR(64) PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    type VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    scheduled_date DATE NOT NULL,
    scheduled_time VARCHAR(16),
    duration_minutes INTEGER,
    surgeon_id VARCHAR(64),
    ot_id VARCHAR(64),
    requirements JSONB,
    checklist JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_surgeries_patient_id ON surgeries(patient_id);
CREATE INDEX IF NOT EXISTS ix_surgeries_surgeon_id ON surgeries(surgeon_id);
CREATE INDEX IF NOT EXISTS ix_surgeries_ot_id ON surgeries(ot_id);

CREATE TABLE IF NOT EXISTS resources (
    id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(32) NOT NULL,
    name VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'available',
    availability JSONB,
    last_updated TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_resources_type ON resources(type);

CREATE TABLE IF NOT EXISTS schedule_slots (
    id VARCHAR(64) PRIMARY KEY,
    surgery_id VARCHAR(64) REFERENCES surgeries(id) ON DELETE SET NULL,
    ot_id VARCHAR(64) NOT NULL,
    slot_date DATE NOT NULL,
    slot_time VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_surgery_id ON schedule_slots(surgery_id);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_ot_id ON schedule_slots(ot_id);

CREATE TABLE IF NOT EXISTS medications (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_name VARCHAR(256) NOT NULL,
    frequency VARCHAR(128),
    next_dose_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_medications_patient_id ON medications(patient_id);

CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_id INTEGER REFERENCES medications(id) ON DELETE SET NULL,
    reminder_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_reminders_patient_id ON reminders(patient_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    user_email VARCHAR(256),
    action VARCHAR(128) NOT NULL,
    resource VARCHAR(256),
    details JSONB,
    timestamp TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log(timestamp);
