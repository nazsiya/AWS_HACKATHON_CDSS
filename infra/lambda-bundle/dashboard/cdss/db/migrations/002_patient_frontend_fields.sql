-- Optional patient fields for frontend alignment (Patients, PatientConsultation, Medications).
-- All nullable and existing rows remain unchanged.

ALTER TABLE patients ADD COLUMN IF NOT EXISTS blood_group VARCHAR(16);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS ward VARCHAR(64);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS severity VARCHAR(32);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS status VARCHAR(32);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS vitals JSONB;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS surgery_readiness JSONB;
