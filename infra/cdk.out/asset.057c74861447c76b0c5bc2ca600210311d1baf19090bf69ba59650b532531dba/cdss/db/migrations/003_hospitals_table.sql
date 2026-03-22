-- CDSS Aurora PostgreSQL migration 003: hospitals table.
-- Adds hospital/facility registry for referral matching and capacity tracking.
-- Aligns with src/cdss/db/models.py Hospital model.

CREATE TABLE IF NOT EXISTS hospitals (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(128) NOT NULL,
    state VARCHAR(128) NOT NULL,
    district VARCHAR(128),
    pincode VARCHAR(10),
    specialties JSONB,
    total_beds INTEGER,
    available_beds INTEGER,
    icu_beds INTEGER,
    available_icu_beds INTEGER,
    tier VARCHAR(32),
    emergency_available BOOLEAN DEFAULT TRUE,
    contact_phone VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hospitals_city ON hospitals(city);
CREATE INDEX IF NOT EXISTS ix_hospitals_state ON hospitals(state);
CREATE INDEX IF NOT EXISTS ix_hospitals_tier ON hospitals(tier);
CREATE INDEX IF NOT EXISTS ix_hospitals_status ON hospitals(status);

-- Add consents table if not already present (from models.py Consent)
CREATE TABLE IF NOT EXISTS consents (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    consent_type VARCHAR(128) NOT NULL,
    purpose VARCHAR(512),
    granted_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_consents_patient_id ON consents(patient_id);
