-- Migration 005: Performance indexes for production readiness
-- Adds indexes on commonly queried columns for fast lookups.

-- Visits (appointments)
CREATE INDEX IF NOT EXISTS idx_visits_patient_id ON visits (patient_id);
CREATE INDEX IF NOT EXISTS idx_visits_doctor_id ON visits (doctor_id);
CREATE INDEX IF NOT EXISTS idx_visits_visit_date ON visits (visit_date);
CREATE INDEX IF NOT EXISTS idx_visits_patient_date ON visits (patient_id, visit_date);

-- Surgeries
CREATE INDEX IF NOT EXISTS idx_surgeries_patient_id ON surgeries (patient_id);
CREATE INDEX IF NOT EXISTS idx_surgeries_surgeon_id ON surgeries (surgeon_id);
CREATE INDEX IF NOT EXISTS idx_surgeries_scheduled_date ON surgeries (scheduled_date);
CREATE INDEX IF NOT EXISTS idx_surgeries_status ON surgeries (status);

-- Schedule slots
CREATE INDEX IF NOT EXISTS idx_schedule_slots_ot_id ON schedule_slots (ot_id);
CREATE INDEX IF NOT EXISTS idx_schedule_slots_slot_date ON schedule_slots (slot_date);
CREATE INDEX IF NOT EXISTS idx_schedule_slots_ot_date ON schedule_slots (ot_id, slot_date);

-- Medications
CREATE INDEX IF NOT EXISTS idx_medications_patient_id ON medications (patient_id);

-- Reminders
CREATE INDEX IF NOT EXISTS idx_reminders_patient_id ON reminders (patient_id);
CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_at ON reminders (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_reminders_sent_at ON reminders (sent_at);

-- Audit log
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log (resource);

-- Patients (commonly searched)
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients (name);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id);
