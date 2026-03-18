-- CDSS Seed Data (SQL)
-- Realistic sample records for development and testing

-- 1. SEED DOCTORS
INSERT INTO doctors (doctor_id, full_name, specialization, department, email, phone_number) VALUES
('DR-1001', 'Dr. Priya Sharma', 'General Medicine', 'Internal Medicine', 'priya.sharma@hospital.com', '+91 99999 11111'),
('DR-1002', 'Dr. Vikram Mehta', 'Internal Medicine', 'Internal Medicine', 'vikram.mehta@hospital.com', '+91 99999 22222'),
('DR-1003', 'Dr. Meena Rao', 'Cardiology', 'Cardiology', 'meena.rao@hospital.com', '+91 99999 33333'),
('DR-1004', 'Dr. Vikram Patel', 'Orthopedics', 'Surgery', 'vikram.patel@hospital.com', '+91 99999 44444');

-- 2. SEED PATIENTS
INSERT INTO patients (patient_id, abdm_id, full_name, date_of_birth, gender, blood_group, phone_number, severity_level, status) VALUES
('PT-1001', 'ABDM-2024-001', 'Rajesh Kumar', '1979-05-12', 'Male', 'B+', '+91 98765 43210', 'moderate', 'waiting'),
('PT-1002', 'ABDM-2024-002', 'Ananya Singh', '1992-08-24', 'Female', 'A+', '+91 87654 32100', 'low', 'in-consultation'),
('PT-1003', 'ABDM-2024-003', 'Mohammed Farhan', '1966-02-15', 'Male', 'O-', '+91 76543 21000', 'critical', 'in-consultation'),
('PT-1004', 'ABDM-2024-004', 'Lakshmi Devi', '1957-11-30', 'Female', 'AB+', '+91 65432 10000', 'high', 'waiting'),
('PT-1005', 'ABDM-2024-005', 'Arjun Nair', '1996-04-10', 'Male', 'B-', '+91 54321 09876', 'moderate', 'scheduled');

-- 3. SEED VITALS
INSERT INTO vitals_history (patient_id, heart_rate, bp_systolic, bp_diastolic, spo2_percent, temperature_f) VALUES
('PT-1001', 78, 130, 85, 97, 98.6),
('PT-1002', 72, 120, 80, 99, 98.2),
('PT-1003', 110, 90, 60, 89, 101.2);

-- 4. SEED APPOINTMENTS
INSERT INTO appointments (appointment_id, patient_id, doctor_id, appointment_time, appointment_type, status, clinical_notes) VALUES
('AP-1001', 'PT-1001', 'DR-1002', CURRENT_TIMESTAMP + interval '2 hours', 'Follow-up', 'scheduled', 'Follow-up for BP and glucose review'),
('AP-1002', 'PT-1002', 'DR-1001', CURRENT_TIMESTAMP + interval '3 hours', 'Consultation', 'scheduled', 'Migraine follow-up'),
('AP-1003', 'PT-1004', 'DR-1003', CURRENT_TIMESTAMP + interval '6 hours', 'Follow-up', 'scheduled', 'INR + medication review');

-- 5. SEED MEDICATIONS
INSERT INTO medications (medication_id, patient_id, prescribed_by, medication_name, dosage, frequency, status, interactions_warning) VALUES
('MD-1001', 'PT-1001', 'DR-1002', 'Metformin', '500mg Tab', 'Twice daily', 'active', NULL),
('MD-1002', 'PT-1001', 'DR-1002', 'Amlodipine', '10mg Tab', 'Once daily', 'active', NULL),
('MD-1003', 'PT-1004', 'DR-1003', 'Warfarin', '5mg Tab', 'Once daily', 'active', 'Warfarin + Aspirin combination detected. High bleeding risk.');

-- 6. SEED SURGERY PLANS
INSERT INTO surgery_plans (surgery_id, patient_id, lead_surgeon_id, surgery_type, complexity_level, estimated_duration_minutes, scheduled_time, status, pre_op_requirements) VALUES
('SR-1001', 'PT-1005', 'DR-1004', 'ACL Reconstruction', 'Moderate', 90, CURRENT_TIMESTAMP + interval '3 days', 'scheduled', 
'{"equipment": ["Arthroscopy tower", "ACL graft system"], "checklist": ["NPO status confirmed", "Consent signed"]}'),
('SR-1002', 'PT-1004', 'DR-1003', 'Cardiac Catheterization', 'High', 120, CURRENT_TIMESTAMP + interval '4 days', 'scheduled',
'{"equipment": ["Fluoroscopy system", "Catheter kit"], "checklist": ["INR checked", "Allergies screened"]}');

-- 7. SEED AI SUMMARIES (Multilingual)
INSERT INTO ai_visit_summaries (summary_id, patient_id, appointment_id, treating_physician, content_json) VALUES
('AI-1001', 'PT-1001', 'AP-1001', 'DR-1002', 
'{
  "abstract": {
    "en": "Your blood pressure was slightly high and your sugar control needs improvement.",
    "hi": "आपका रक्तचाप थोड़ा अधिक था और शुगर नियंत्रण में सुधार की जरूरत है।",
    "ta": "உங்கள் இரத்த அழுத்தம் சிறிது அதிகமாக இருந்தது; சர்க்கரை கட்டுப்பாட்டில் மேம்பாடு தேவை."
  },
  "tips": {
    "en": ["Take medicines at the same time daily.", "Limit salt and sugary foods."],
    "hi": ["दवाएँ रोज़ एक ही समय पर लें।", "नमक और मीठे खाद्य पदार्थ सीमित करें।"],
    "ta": ["மருந்துகளை தினமும் ஒரே நேரத்தில் எடுத்துக் கொள்ளுங்கள்.", "உப்பு மற்றும் சர்க்கரை அதிகமான உணவை குறைக்கவும்."]
  }
}');

-- 8. SEED INVENTORY
INSERT INTO inventory (item_id, item_name, category, total_quantity, available_quantity, location, status) VALUES
('INV-1001', 'Arthroscopy Tower', 'Equipment', 5, 3, 'Surgery Block A', 'available'),
('INV-1002', 'Laparoscopic Set', 'Instrument', 10, 8, 'OT Room 2', 'available'),
('INV-1003', 'Defibrillator', 'Equipment', 4, 3, 'ICU', 'available'),
('INV-1004', 'N95 Masks', 'Consumable', 500, 450, 'Main Store', 'available'),
('INV-1005', 'Surgical Sutures', 'Consumable', 200, 180, 'Surgical Ward', 'available');
