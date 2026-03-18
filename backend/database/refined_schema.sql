-- CDSS Refined Clinical Database Schema (PostgreSQL)
-- This schema supports role-based access, intelligent surgical workflows, 
-- and AI-powered patient engagement.

-- 1. DOCTORS TABLE
-- Stores profile information for healthcare providers
CREATE TABLE doctors (
    doctor_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. PATIENTS TABLE
-- Stores patient records with DISHA (Digital Information Security in Healthcare Act) compliance awareness
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    abdm_id VARCHAR(50) UNIQUE, -- Ayushman Bharat Digital Mission ID
    full_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    blood_group VARCHAR(5),
    phone_number VARCHAR(20),
    address TEXT,
    preferred_language VARCHAR(10) DEFAULT 'en',
    ward_number VARCHAR(20),
    severity_level VARCHAR(20) DEFAULT 'low', -- low, moderate, high, critical
    status VARCHAR(20) DEFAULT 'waiting', -- waiting, in-consultation, scheduled, admitted, discharged
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. APPOINTMENTS TABLE
-- Manages scheduling between doctors and patients
CREATE TABLE appointments (
    appointment_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    doctor_id VARCHAR(50) NOT NULL REFERENCES doctors(doctor_id) ON DELETE SET NULL,
    appointment_time TIMESTAMP WITH TIME ZONE NOT NULL,
    appointment_type VARCHAR(50) DEFAULT 'Consultation', -- Consultation, Follow-up, Procedure, Emergency
    status VARCHAR(20) DEFAULT 'scheduled', -- scheduled, completed, cancelled, no-show
    clinical_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. SURGERY_PLANS TABLE
-- Detailed coordination for surgical procedures
CREATE TABLE surgery_plans (
    surgery_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    lead_surgeon_id VARCHAR(50) NOT NULL REFERENCES doctors(doctor_id) ON DELETE SET NULL,
    surgery_type VARCHAR(200) NOT NULL,
    complexity_level VARCHAR(20) DEFAULT 'Moderate', -- Low, Moderate, High
    estimated_duration_minutes INT DEFAULT 60,
    ot_room_id VARCHAR(50),
    scheduled_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'scheduled', -- scheduled, in-prep, pre-op, active, completed, cancelled
    pre_op_requirements JSONB, -- JSON storage for equipment and checklist
    risk_factors TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. MEDICATIONS TABLE
-- Tracks prescriptions and adherence
CREATE TABLE medications (
    medication_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    prescribed_by VARCHAR(50) REFERENCES doctors(doctor_id) ON DELETE SET NULL,
    medication_name VARCHAR(200) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100), -- e.g., 'Twice daily', 'Every 6 hours'
    start_date DATE,
    end_date DATE,
    instructions TEXT,
    status VARCHAR(20) DEFAULT 'active', -- active, completed, discontinued
    interactions_warning TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. AI_VISIT_SUMMARIES TABLE
-- Stores AI-generated summaries in multiple languages
CREATE TABLE ai_visit_summaries (
    summary_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    appointment_id VARCHAR(50) REFERENCES appointments(appointment_id),
    visit_date DATE DEFAULT CURRENT_DATE,
    treating_physician VARCHAR(50) REFERENCES doctors(doctor_id),
    content_json JSONB, -- Stores multilingual data (en, hi, ta) for abstract, reasoning, tips, cautions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. VITALS_HISTORY TABLE
-- Time-series data for patient health monitoring
CREATE TABLE vitals_history (
    vital_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    heart_rate INT,
    bp_systolic INT,
    bp_diastolic INT,
    spo2_percent INT,
    temperature_f NUMERIC(5,2),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. INVENTORY TABLE
-- Tracks medical equipment and consumables as per Requirement 4
CREATE TABLE inventory (
    item_id VARCHAR(50) PRIMARY KEY,
    item_name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL, -- Equipment, Consumable, Instrument
    total_quantity INT DEFAULT 0,
    available_quantity INT DEFAULT 0,
    location VARCHAR(100),
    status VARCHAR(50) DEFAULT 'available', -- available, busy, maintenance, depleted
    last_inspected_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES for Performance Optimization
CREATE INDEX idx_patients_abdm_id ON patients(abdm_id);
CREATE INDEX idx_appointments_time ON appointments(appointment_time);
CREATE INDEX idx_surgery_scheduled ON surgery_plans(scheduled_time);
CREATE INDEX idx_vitals_patient_time ON vitals_history(patient_id, recorded_at);
CREATE INDEX idx_medications_patient ON medications(patient_id);
CREATE INDEX idx_inventory_status ON inventory(status);

-- TRIGGER for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_doctors_modtime BEFORE UPDATE ON doctors FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_patients_modtime BEFORE UPDATE ON patients FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_appointments_modtime BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_surgery_plans_modtime BEFORE UPDATE ON surgery_plans FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_medications_modtime BEFORE UPDATE ON medications FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_inventory_modtime BEFORE UPDATE ON inventory FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
