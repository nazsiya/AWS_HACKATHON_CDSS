-- CDSS Full Schema – Frontend API Alignment (PostgreSQL)
-- Reference DDL matching src/cdss/db/models.py. Use to create DB from scratch or validate schema.
-- Run after creating database: psql -d cdssdb -f schema_frontend_alignment.sql

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. patients
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    date_of_birth DATE,
    gender VARCHAR(32),
    language VARCHAR(16),
    abha_id VARCHAR(64) UNIQUE,
    conditions JSONB,
    allergies JSONB,
    vitals JSONB,
    blood_group VARCHAR(16),
    ward VARCHAR(64),
    severity VARCHAR(32),
    status VARCHAR(64),
    surgery_readiness JSONB,
    address_json JSONB,
    emergency_contact_json JSONB,
    last_visit TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_patients_abha_id ON patients(abha_id);
CREATE INDEX IF NOT EXISTS ix_patients_updated_at ON patients(updated_at);

-- 2. visits (consultations)
CREATE TABLE IF NOT EXISTS visits (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id VARCHAR(128) NOT NULL,
    visit_date DATE,
    notes TEXT,
    summary TEXT,
    extracted_entities JSONB,
    transcript_s3_key VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_visits_patient_id ON visits(patient_id);
CREATE INDEX IF NOT EXISTS ix_visits_doctor_id ON visits(doctor_id);

-- 3. surgeries
CREATE TABLE IF NOT EXISTS surgeries (
    id VARCHAR(64) PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    type VARCHAR(128) NOT NULL,
    surgeon_id VARCHAR(128),
    ot_id VARCHAR(64),
    scheduled_date DATE,
    scheduled_time VARCHAR(32),
    duration_minutes INTEGER,
    status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    checklist JSONB,
    requirements JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_surgeries_patient_id ON surgeries(patient_id);
CREATE INDEX IF NOT EXISTS ix_surgeries_surgeon_id ON surgeries(surgeon_id);
CREATE INDEX IF NOT EXISTS ix_surgeries_ot_id ON surgeries(ot_id);
CREATE INDEX IF NOT EXISTS ix_surgeries_scheduled ON surgeries(scheduled_date, scheduled_time);

-- 4. resources (OTs, equipment, staff)
CREATE TABLE IF NOT EXISTS resources (
    id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(32) NOT NULL,
    name VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'available',
    availability JSONB,
    last_updated TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_resources_type ON resources(type);

-- 5. schedule_slots
CREATE TABLE IF NOT EXISTS schedule_slots (
    id SERIAL PRIMARY KEY,
    ot_id VARCHAR(64),
    slot_date DATE,
    slot_time VARCHAR(32),
    surgery_id VARCHAR(64) REFERENCES surgeries(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'available',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_surgery_id ON schedule_slots(surgery_id);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_ot_id ON schedule_slots(ot_id);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_date_time ON schedule_slots(slot_date, slot_time);

-- 6. medications
CREATE TABLE IF NOT EXISTS medications (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_name VARCHAR(256) NOT NULL,
    frequency VARCHAR(64),
    next_dose_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_medications_patient_id ON medications(patient_id);

-- 7. reminders
CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_id INTEGER REFERENCES medications(id) ON DELETE SET NULL,
    reminder_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_reminders_patient_id ON reminders(patient_id);
CREATE INDEX IF NOT EXISTS ix_reminders_reminder_at ON reminders(reminder_at);

-- 8. audit_log (admin/audit + POST /api/v1/activity)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    user_email VARCHAR(256),
    action VARCHAR(512) NOT NULL,
    resource VARCHAR(512) NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);
CREATE INDEX IF NOT EXISTS ix_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log(timestamp DESC);

-- 9. hospitals (optional, for /api/v1/hospitals)
CREATE TABLE IF NOT EXISTS hospitals (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    city VARCHAR(128),
    state VARCHAR(128),
    specialties JSONB,
    available_beds INTEGER,
    icu_beds INTEGER,
    available_icu_beds INTEGER,
    tier VARCHAR(32),
    emergency_available BOOLEAN,
    contact_phone VARCHAR(64),
    latitude VARCHAR(32),
    longitude VARCHAR(32),
    status VARCHAR(16) NOT NULL DEFAULT 'active'
);

-- 10. alert_log (Req 9 – optional)
CREATE TABLE IF NOT EXISTS alert_log (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL UNIQUE,
    severity VARCHAR(16) NOT NULL,
    alert_type VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    patient_id VARCHAR(32),
    doctor_id VARCHAR(128),
    message TEXT,
    payload JSONB,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 11. agent_event_log (Req 8 – optional)
CREATE TABLE IF NOT EXISTS agent_event_log (
    id SERIAL PRIMARY KEY,
    correlation_id VARCHAR(64) NOT NULL,
    source_agent VARCHAR(64) NOT NULL,
    target_agent VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_agent_event_log_correlation ON agent_event_log(correlation_id);

-- Trigger for updated_at on patients and surgeries
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_patients_updated_at ON patients;
CREATE TRIGGER update_patients_updated_at
  BEFORE UPDATE ON patients FOR EACH ROW EXECUTE PROCEDURE update_updated_at();

DROP TRIGGER IF EXISTS update_surgeries_updated_at ON surgeries;
CREATE TRIGGER update_surgeries_updated_at
  BEFORE UPDATE ON surgeries FOR EACH ROW EXECUTE PROCEDURE update_updated_at();
