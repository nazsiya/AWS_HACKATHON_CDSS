// Mock data for the CDSS Doctor Dashboard

export const currentDoctor = {
  id: 'DR-001',
  name: 'Dr. Priya Sharma',
  specialization: 'General Medicine',
  department: 'Internal Medicine',
  avatar: null,
  initials: 'PS',
};

export const patients = [
  {
    id: 'PT-1001',
    name: 'Rajesh Kumar',
    age: 45,
    gender: 'Male',
    bloodGroup: 'B+',
    contact: '+91 98765 43210',
    abdmId: 'ABDM-2024-001',
    ward: 'General',
    severity: 'moderate',
    vitals: { hr: 78, bp: '130/85', spo2: 97, temp: 98.6 },
    conditions: ['Type 2 Diabetes', 'Hypertension'],
    lastVisit: '2026-02-28',
    nextAppointment: '2026-03-01T10:30:00',
    nextAppointmentDetails: {
      doctorName: 'Dr. Vikram Mehta',
      department: 'Internal Medicine',
      notes: 'Follow-up for BP and glucose review',
    },
    status: 'waiting',
    adherence: 0.92,
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 2,
      medicationAdherenceStatus: 'Good compliance',
      weeklyAdherence: 0.86,
      aiVisitSummary: {
        available: true,
        agentName: 'MedAI Summary Agent',
        lastVisitDate: '2026-02-28',
        treatingPhysician: 'Dr. Vikram Mehta',
        sections: {
          abstract: {
            en: 'Your blood pressure was slightly high and your sugar control needs improvement. Your doctor adjusted one medicine and advised diet changes.',
            hi: 'आपका रक्तचाप थोड़ा अधिक था और शुगर नियंत्रण में सुधार की जरूरत है। डॉक्टर ने एक दवा की खुराक बदली और आहार में बदलाव की सलाह दी।',
            ta: 'உங்கள் இரத்த அழுத்தம் சிறிது அதிகமாக இருந்தது; சர்க்கரை கட்டுப்பாட்டில் மேம்பாடு தேவை. மருத்துவர் ஒரு மருந்தை மாற்றி உணவு முறையைப் பற்றி ஆலோசனை வழங்கினார்.',
          },
          reasoning: {
            en: 'The medication dose was increased to improve blood pressure control while keeping your diabetes medicines unchanged for now.',
            hi: 'रक्तचाप को बेहतर नियंत्रित करने के लिए दवा की खुराक बढ़ाई गई, जबकि फिलहाल डायबिटीज़ की दवाएँ वही रखी गईं।',
            ta: 'இரத்த அழுத்தக் கட்டுப்பாட்டை மேம்படுத்த மருந்தளவு உயர்த்தப்பட்டது; நீரிழிவு மருந்துகள் தற்போது மாற்றப்படவில்லை.',
          },
          tips: {
            en: [
              'Take medicines at the same time daily.',
              'Limit salt and sugary foods.',
              'Walk 20–30 minutes most days (if safe for you).',
            ],
            hi: [
              'दवाएँ रोज़ एक ही समय पर लें।',
              'नमक और मीठे खाद्य पदार्थ सीमित करें।',
              'अधिकांश दिनों में 20–30 मिनट टहलें (यदि आपके लिए सुरक्षित हो)।',
            ],
            ta: [
              'மருந்துகளை தினமும் ஒரே நேரத்தில் எடுத்துக் கொள்ளுங்கள்.',
              'உப்பு மற்றும் சர்க்கரை அதிகமான உணவை குறைக்கவும்.',
              'பல நாட்களில் 20–30 நிமிடம் நடைபயிற்சி செய்யுங்கள் (உங்களுக்கு பாதுகாப்பானால்).',
            ],
          },
          cautions: {
            en: [
              'Seek care urgently if you have chest pain, severe breathlessness, or fainting.',
              'Report dizziness or swelling after the dose change.',
            ],
            hi: [
              'सीने में दर्द, तेज़ सांस फूलना, या बेहोशी हो तो तुरंत चिकित्सा लें।',
              'खुराक बदलने के बाद चक्कर या सूजन हो तो डॉक्टर को बताएं।',
            ],
            ta: [
              'மார்பு வலி, கடுமையான மூச்சுத்திணறல், அல்லது மயக்கம் இருந்தால் உடனடி மருத்துவ உதவி பெறுங்கள்.',
              'மருந்தளவு மாற்றத்திற்குப் பிறகு தலைச்சுற்றல் அல்லது வீக்கம் இருந்தால் மருத்துவரிடம் தெரிவிக்கவும்.',
            ],
          },
        },
      },
      todayMedications: [
        { id: 'dose-pt1001-1', medicine: 'Metformin', dosage: '500mg Tab', time: '08:00', status: 'Taken' },
        { id: 'dose-pt1001-2', medicine: 'Metformin', dosage: '500mg Tab', time: '20:00', status: 'Pending' },
        { id: 'dose-pt1001-3', medicine: 'Amlodipine', dosage: '10mg Tab', time: '09:00', status: 'Missed' },
      ],
      appointments: {
        upcoming: [
          {
            id: 'apt-pt1001-1',
            doctorName: 'Dr. Vikram Mehta',
            department: 'Internal Medicine',
            dateTime: '2026-03-01T10:30:00',
            clinicalNotes: 'BP + HbA1c review',
          },
          {
            id: 'apt-pt1001-2',
            doctorName: 'Dr. Priya Sharma',
            department: 'General Medicine',
            dateTime: '2026-03-08T09:30:00',
            clinicalNotes: 'Medication adherence follow-up',
          },
        ],
        past: [
          {
            id: 'visit-pt1001-1',
            doctorName: 'Dr. Priya Sharma',
            department: 'Internal Medicine',
            dateTime: '2026-02-28T10:00:00',
            summaryAvailable: true,
          },
          {
            id: 'visit-pt1001-2',
            doctorName: 'Dr. Priya Sharma',
            department: 'Internal Medicine',
            dateTime: '2026-02-15T10:00:00',
            summaryAvailable: true,
          },
        ],
      },
    },
    surgeryReadiness: {
      preOpStatus: 'pending',
      riskFactors: ['Type 2 Diabetes — glycemic control required', 'Hypertension — BP at 130/85'],
      lastAssessed: '2026-02-28',
    },
  },
  {
    id: 'PT-1002',
    name: 'Ananya Singh',
    age: 32,
    gender: 'Female',
    bloodGroup: 'A+',
    contact: '+91 87654 32100',
    abdmId: 'ABDM-2024-002',
    ward: 'OPD',
    severity: 'low',
    vitals: { hr: 72, bp: '120/80', spo2: 99, temp: 98.2 },
    conditions: ['Migraine'],
    lastVisit: '2026-02-25',
    nextAppointment: '2026-03-01T11:00:00',
    nextAppointmentDetails: {
      doctorName: 'Dr. Priya Sharma',
      department: 'General Medicine',
      notes: 'Migraine follow-up',
    },
    status: 'in-consultation',
    adherence: 1.0,
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 1,
      medicationAdherenceStatus: 'Excellent',
      weeklyAdherence: 0.95,
      aiVisitSummary: {
        available: true,
        agentName: 'MedAI Summary Agent',
        lastVisitDate: '2026-02-25',
        treatingPhysician: 'Dr. Priya Sharma',
        sections: {
          abstract: 'Your migraine symptoms were reviewed and a trigger-avoidance plan was discussed.',
          reasoning: 'The treatment plan focuses on symptom control and identifying triggers.',
          tips: ['Stay hydrated.', 'Maintain regular sleep.', 'Track triggers in a diary.'],
          cautions: ['Seek care if headaches are sudden/severe or with weakness/vision changes.'],
        },
      },
      todayMedications: [{ id: 'dose-pt1002-1', medicine: 'Naproxen', dosage: '250mg Tab', time: '10:00', status: 'Pending' }],
      appointments: {
        upcoming: [
          {
            id: 'apt-pt1002-1',
            doctorName: 'Dr. Priya Sharma',
            department: 'General Medicine',
            dateTime: '2026-03-01T11:00:00',
            clinicalNotes: 'Migraine check-in',
          },
        ],
        past: [],
      },
    },
  },
  {
    id: 'PT-1003',
    name: 'Mohammed Farhan',
    age: 58,
    gender: 'Male',
    bloodGroup: 'O-',
    contact: '+91 76543 21000',
    abdmId: 'ABDM-2024-003',
    ward: 'ICU',
    severity: 'critical',
    vitals: { hr: 110, bp: '90/60', spo2: 89, temp: 101.2 },
    conditions: ['Pneumonia', 'COPD', 'Sepsis Suspected'],
    lastVisit: '2026-03-01',
    nextAppointment: null,
    status: 'in-consultation',
    adherence: 0.78,
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 2,
      medicationAdherenceStatus: 'Needs attention',
      weeklyAdherence: 0.7,
      aiVisitSummary: { available: false, agentName: 'MedAI Summary Agent', lastVisitDate: '2026-03-01', treatingPhysician: '—', sections: {} },
      todayMedications: [
        { id: 'dose-pt1003-1', medicine: 'Azithromycin', dosage: '500mg Tab', time: '10:00', status: 'Pending' },
        { id: 'dose-pt1003-2', medicine: 'Salbutamol', dosage: 'Nebulization', time: '12:00', status: 'Pending' },
      ],
      appointments: { upcoming: [], past: [] },
    },
  },
  {
    id: 'PT-1004',
    name: 'Lakshmi Devi',
    age: 67,
    gender: 'Female',
    bloodGroup: 'AB+',
    contact: '+91 65432 10000',
    abdmId: 'ABDM-2024-004',
    ward: 'Cardiology',
    severity: 'high',
    vitals: { hr: 95, bp: '150/95', spo2: 94, temp: 99.1 },
    conditions: ['Atrial Fibrillation', 'Heart Failure (Class II)'],
    lastVisit: '2026-02-27',
    nextAppointment: '2026-03-01T14:00:00',
    nextAppointmentDetails: {
      doctorName: 'Dr. Meena Rao',
      department: 'Cardiology',
      notes: 'INR + medication review',
    },
    status: 'waiting',
    adherence: 0.65,
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 2,
      medicationAdherenceStatus: 'Low compliance',
      weeklyAdherence: 0.62,
      aiVisitSummary: { available: true, agentName: 'MedAI Summary Agent', lastVisitDate: '2026-02-27', treatingPhysician: 'Dr. Meena Rao', sections: {} },
      todayMedications: [
        { id: 'dose-pt1004-1', medicine: 'Warfarin', dosage: '5mg Tab', time: '20:00', status: 'Pending' },
        { id: 'dose-pt1004-2', medicine: 'Digoxin', dosage: '0.25mg Tab', time: '09:00', status: 'Taken' },
      ],
      appointments: { upcoming: [], past: [] },
    },
  },
  {
    id: 'PT-1005',
    name: 'Arjun Nair',
    age: 28,
    gender: 'Male',
    bloodGroup: 'B-',
    contact: '+91 54321 09876',
    abdmId: 'ABDM-2024-005',
    ward: 'Ortho',
    severity: 'moderate',
    vitals: { hr: 80, bp: '125/82', spo2: 98, temp: 98.8 },
    conditions: ['ACL Tear — Left Knee'],
    lastVisit: '2026-02-20',
    nextAppointment: '2026-03-02T09:00:00',
    nextAppointmentDetails: {
      doctorName: 'Dr. Vikram Patel',
      department: 'Orthopedics',
      notes: 'Pre-op check',
    },
    status: 'scheduled',
    surgeryReadiness: {
      preOpStatus: 'cleared',
      riskFactors: ['ACL reconstruction — routine pre-op done'],
      lastAssessed: '2026-02-25',
    },
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 1,
      medicationAdherenceStatus: 'Good compliance',
      weeklyAdherence: 0.88,
      aiVisitSummary: { available: false, agentName: 'MedAI Summary Agent', lastVisitDate: '2026-02-20', treatingPhysician: 'Dr. Vikram Patel', sections: {} },
      todayMedications: [{ id: 'dose-pt1005-1', medicine: 'Pain reliever', dosage: 'As prescribed', time: '21:00', status: 'Pending' }],
      appointments: { upcoming: [], past: [] },
    },
  },
  {
    id: 'PT-1006',
    name: 'Fatima Begum',
    age: 40,
    gender: 'Female',
    bloodGroup: 'A-',
    contact: '+91 43210 98765',
    abdmId: 'ABDM-2024-006',
    ward: 'General',
    severity: 'low',
    vitals: { hr: 70, bp: '118/76', spo2: 99, temp: 98.4 },
    conditions: ['Hypothyroidism', 'Vitamin D Deficiency'],
    lastVisit: '2026-02-15',
    nextAppointment: '2026-03-01T15:30:00',
    status: 'waiting',
    portal: {
      preferredLanguage: 'en',
      activePrescriptionsCount: 1,
      medicationAdherenceStatus: 'Good compliance',
      weeklyAdherence: 0.9,
      aiVisitSummary: { available: false, agentName: 'MedAI Summary Agent', lastVisitDate: '2026-02-15', treatingPhysician: '—', sections: {} },
      todayMedications: [{ id: 'dose-pt1006-1', medicine: 'Levothyroxine', dosage: '50mcg Tab', time: '06:00', status: 'Taken' }],
      appointments: { upcoming: [], past: [] },
    },
  },
];

export const todaySchedule = [
  { time: '09:00', patient: 'Rajesh Kumar', type: 'Follow-up', status: 'completed' },
  { time: '09:30', patient: 'Walk-in slot', type: 'Open', status: 'open' },
  { time: '10:00', patient: 'Ananya Singh', type: 'Consultation', status: 'in-progress' },
  { time: '10:30', patient: 'Rajesh Kumar', type: 'Lab Review', status: 'upcoming' },
  { time: '11:00', patient: 'Mohammed Farhan', type: 'Emergency', status: 'upcoming' },
  { time: '11:30', patient: 'Lakshmi Devi', type: 'Follow-up', status: 'upcoming' },
  { time: '14:00', patient: 'Fatima Begum', type: 'Consultation', status: 'upcoming' },
  { time: '15:30', patient: 'Arjun Nair', type: 'Pre-op Check', status: 'upcoming' },
];

/** For dashboard / AI: clinical alerts */
export const aiAlerts = [
  {
    id: 'alert-1',
    type: 'critical',
    title: 'Drug Interaction Warning',
    message: 'Warfarin + Aspirin combination detected for Lakshmi Devi. High bleeding risk.',
    patient: 'Lakshmi Devi',
    time: '2 min ago',
  },
  {
    id: 'alert-2',
    type: 'warning',
    title: 'Abnormal Vitals',
    message: 'Mohammed Farhan SpO2 dropped to 89%. Consider oxygen supplementation.',
    patient: 'Mohammed Farhan',
    time: '5 min ago',
  },
  {
    id: 'alert-3',
    type: 'info',
    title: 'Lab Results Available',
    message: 'HbA1c results for Rajesh Kumar: 7.8% (above target). Consider medication adjustment.',
    patient: 'Rajesh Kumar',
    time: '15 min ago',
  },
  {
    id: 'alert-4',
    type: 'success',
    title: 'Surgery Cleared',
    message: 'Pre-op assessment complete for Arjun Nair ACL reconstruction. OT-3 booked for March 5.',
    patient: 'Arjun Nair',
    time: '30 min ago',
  },
  {
    id: 'alert-5',
    type: 'warning',
    title: 'Adherence escalation',
    message: 'Lakshmi Devi: adherence 65% — 3 missed doses. Consider nudge or follow-up.',
    patient: 'Lakshmi Devi',
    time: '1 hr ago',
  },
  {
    id: 'alert-6',
    type: 'warning',
    title: 'OT conflict',
    message: 'OT-1 double-booked on Mar 5 09:00. Resolve in Admin → Analytics.',
    patient: '—',
    time: '2 hr ago',
  },
];

/** Clinical updates for dashboard: type, title, patient, description, time, priority */
export const clinicalUpdates = [
  { id: 'cu3', type: 'discharge_pending', title: 'Discharge Pending', patientName: 'Lakshmi Devi', description: 'Discharge summary and prescriptions pending sign-off.', time: '1 hr ago', priority: 'moderate' },
  { id: 'cu4', type: 'upcoming_surgery', title: 'Upcoming Surgery', patientName: 'Arjun Nair', description: 'ACL reconstruction — Pre-op cleared. OT-3, March 5.', time: '30 min ago', priority: 'info' },
  { id: 'cu5', type: 'follow_up_reminder', title: 'Follow-up Reminder', patientName: 'Ananya Singh', description: 'Routine follow-up due in 2 days. Diabetic care review.', time: '2 hr ago', priority: 'normal' },
];

/** Doctor's tasks for the day: id, priority (High|Medium|Low), taskType, patientName — used by Dashboard "Doctor's Tasks" section */
export const pendingClinicalTasks = [
  { id: 't1', priority: 'High', taskType: 'Discharge summary', patientName: 'Lakshmi Devi' },
  { id: 't2', priority: 'High', taskType: 'Lab review', patientName: 'Mohammed Farhan' },
  { id: 't3', priority: 'Medium', taskType: 'Pre-op check', patientName: 'Arjun Nair' },
  { id: 't4', priority: 'Medium', taskType: 'Prescription sign-off', patientName: 'Rajesh Kumar' },
  { id: 't5', priority: 'Low', taskType: 'Follow-up reminder', patientName: 'Ananya Singh' },
];

/** Clinical alerts only (no AI marketing / Global Risk Pulse) for dashboard */
export const clinicalAlerts = aiAlerts.filter(
  (a) => ['critical', 'warning', 'info', 'success'].includes(a.type)
);

// ─── Operations-focused Dashboard (no AI/risk) ───

export const dashboardOverview = {
  todayAppointments: 18,
  totalPatients: 210,
  patientsAttended: 12,
  surgeriesScheduled: 5,
  pendingCaseNotes: 3,
  shiftHoursRemaining: 4,
  updatedAt: '5 mins ago',
  stats: {
    appointments: [10, 12, 15, 14, 16, 18],
    patients: [180, 200, 190, 220, 210, 210],
    attended: [8, 10, 9, 11, 10, 12],
    surgeries: [2, 3, 2, 4, 3, 5]
  }
};

/** Appointment Activity for new dashboard table */
export const appointmentActivity = [
  {
    id: 1,
    name: 'Leslie Alexander',
    age: 25,
    fees: '$25/h',
    date: '10/10/2020',
    visitTime: '09:15-09:45am',
    doctor: 'Dr. Jacob Jones',
    conditions: 'Mumps Stage II',
    avatar: 'https://i.pravatar.cc/150?u=leslie'
  },
  {
    id: 2,
    name: 'Ronald Richards',
    age: 43,
    fees: '$25/h',
    date: '10/12/2020',
    visitTime: '12:00-12:45pm',
    doctor: 'Dr. Theresa Webb',
    conditions: 'Depression',
    avatar: 'https://i.pravatar.cc/150?u=ronald'
  },
  {
    id: 3,
    name: 'Jane Cooper',
    age: 55,
    fees: '$25/h',
    date: '10/13/2020',
    visitTime: '01:15-01:45pm',
    doctor: 'Dr. Jacob Jones',
    conditions: 'Arthritis',
    avatar: 'https://i.pravatar.cc/150?u=jane'
  },
  {
    id: 4,
    name: 'Robert Fox',
    age: 23,
    fees: '$25/h',
    date: '10/14/2020',
    visitTime: '02:00-02:45pm',
    doctor: 'Dr. Arlene McCoy',
    conditions: 'Fracture',
    avatar: 'https://i.pravatar.cc/150?u=robert'
  },
  {
    id: 5,
    name: 'Jenny Wilson',
    age: 29,
    fees: '$25/h',
    date: '10/15/2020',
    visitTime: '12:00-12:45pm',
    doctor: 'Dr. Esther Howard',
    conditions: 'Depression',
    avatar: 'https://i.pravatar.cc/150?u=jenny'
  },
];

/** Operational alerts only: shift, staffing, emergency, escalation. No AI/clinical risk. */
export const operationalAlerts = [
  {
    id: 'op-2',
    type: 'shift',
    title: 'Shift extended',
    message: 'Shift extended by 2 hours (Overtime approved).',
    time: '09:00',
    action: 'Acknowledge',
  },
  {
    id: 'op-3',
    type: 'emergency',
    title: 'Emergency admission',
    message: 'Emergency admission assigned to you.',
    time: '11:45',
    action: null,
  },
  {
    id: 'op-4',
    type: 'shift',
    title: 'OT rescheduled',
    message: 'OT rescheduled to 4:30 PM.',
    time: '10:30',
    action: 'View',
  },
  {
    id: 'op-5',
    type: 'info',
    title: 'Nurse escalation request',
    message: 'Nurse escalation request pending.',
    time: '11:00',
    action: 'View',
  },
  {
    id: 'op-6',
    type: 'info',
    title: 'ICU transfer request',
    message: 'ICU transfer request requires your approval.',
    time: '11:20',
    action: 'Acknowledge',
  },
];

/** Exactly 3 alerts for clean dashboard: Staffing (View), Shift (Acknowledge), Emergency (no button). */
export const vitalAlertsThree = operationalAlerts.slice(0, 3);

/** Checklist-style pending tasks (no AI recommendations). */
export const pendingTasksChecklist = [
  { id: 'ck-1', label: 'Complete discharge summary', done: false },
  { id: 'ck-2', label: 'Review lab results', done: false },
  { id: 'ck-3', label: 'Sign prescriptions', done: false },
  { id: 'ck-4', label: 'Approve surgery notes', done: false },
];

/** My Patients Today for dashboard table: name, room, condition, priority. */
export const myPatientsToday = [
  { id: 'PT-1001', name: 'Rajesh Kumar', room: 'Ward 4', condition: 'Type 2 Diabetes, Hypertension', priority: 'High' },
  { id: 'PT-1002', name: 'Ananya Singh', room: 'OPD-2', condition: 'Migraine', priority: 'Low' },
  { id: 'PT-1003', name: 'Mohammed Farhan', room: 'ICU', condition: 'Pneumonia, COPD', priority: 'High' },
  { id: 'PT-1004', name: 'Lakshmi Devi', room: 'Cardiology', condition: 'Atrial Fibrillation, Heart Failure', priority: 'High' },
  { id: 'PT-1005', name: 'Arjun Nair', room: 'Ortho', condition: 'ACL Tear — Left Knee', priority: 'Medium' },
  { id: 'PT-1006', name: 'Fatima Begum', room: 'Ward 2', condition: 'Hypothyroidism', priority: 'Low' },
];

export const consultationHistory = [
  {
    id: 'consult-1',
    patientId: 'PT-1001',
    date: '2026-02-28',
    doctor: 'Dr. Priya Sharma',
    notes: 'Patient reports persistent headaches. BP elevated at 130/85. Adjusted Amlodipine from 5mg to 10mg. Advised low-sodium diet.',
    aiSummary: 'Hypertensive patient with suboptimal BP control. Medication dose escalated. Diet counseling provided.',
    prescriptions: [
      { medication: 'Amlodipine', dosage: '10mg', frequency: 'Once daily', duration: '30 days' },
      { medication: 'Metformin', dosage: '500mg', frequency: 'Twice daily', duration: '30 days' },
    ],
  },
  {
    id: 'consult-2',
    patientId: 'PT-1001',
    date: '2026-02-15',
    doctor: 'Dr. Priya Sharma',
    notes: 'Routine follow-up. Blood sugar fasting: 145mg/dL. HbA1c: 7.2%. Continue current medications.',
    aiSummary: 'Diabetic control is moderate. Glycemic targets not yet achieved. Current regimen maintained.',
    prescriptions: [
      { medication: 'Metformin', dosage: '500mg', frequency: 'Twice daily', duration: '30 days' },
      { medication: 'Amlodipine', dosage: '5mg', frequency: 'Once daily', duration: '30 days' },
    ],
  },
];

export const surgeries = [
  {
    id: 'SRG-001',
    patient: 'Arjun Nair',
    type: 'ACL Reconstruction',
    complexity: 'Moderate',
    estimatedDuration: '90 min',
    ot: 'OT-3',
    date: '2026-03-05',
    time: '09:00',
    status: 'scheduled',
    surgeon: 'Dr. Vikram Patel',
    preOpRequirements: {
      equipment: ['Arthroscopy tower', 'ACL graft system', 'Surgical drill', 'Cams'],
      checklist: ['NPO status confirmed', 'Consent signed', 'Marking done', 'Prophylactic antibiotics given']
    }
  },
  {
    id: 'SRG-002',
    patient: 'Lakshmi Devi',
    type: 'Cardiac Catheterization',
    complexity: 'High',
    estimatedDuration: '120 min',
    ot: 'OT-1',
    date: '2026-03-06',
    time: '10:00',
    status: 'pre-op',
    surgeon: 'Dr. Meena Rao',
    preOpRequirements: {
      equipment: ['Fluoroscopy system', 'Catheter kit', 'Contrast media', 'Monitoring sensors'],
      checklist: ['INR checked', 'Renal function verified', 'Allergies screened', 'Consent signed']
    }
  },
  {
    id: 'SRG-003',
    patient: 'Unknown',
    type: 'Appendectomy',
    complexity: 'Low',
    estimatedDuration: '60 min',
    ot: 'OT-2',
    date: '2026-03-04',
    time: '14:00',
    status: 'in-prep',
    surgeon: 'Dr. Priya Sharma',
    preOpRequirements: {
      equipment: ['Laparoscopic set', 'Endoclip applier', 'Suction irrigator'],
      checklist: ['General anesthesia clearance', 'NPO status', 'Consent signed', 'Skin prep done']
    }
  },
];

export const medications = [
  { id: 'MED-001', patient: 'Rajesh Kumar', medication: 'Metformin 500mg', frequency: 'Twice daily', nextDose: '2026-03-01T13:00:00', status: 'on-time', interactions: [] },
  { id: 'MED-002', patient: 'Rajesh Kumar', medication: 'Amlodipine 10mg', frequency: 'Once daily', nextDose: '2026-03-01T08:00:00', status: 'overdue', interactions: [] },
  { id: 'MED-003', patient: 'Lakshmi Devi', medication: 'Warfarin 5mg', frequency: 'Once daily', nextDose: '2026-03-01T20:00:00', status: 'on-time', interactions: ['Aspirin — HIGH RISK'] },
  { id: 'MED-004', patient: 'Lakshmi Devi', medication: 'Digoxin 0.25mg', frequency: 'Once daily', nextDose: '2026-03-01T09:00:00', status: 'given', interactions: [] },
  { id: 'MED-005', patient: 'Mohammed Farhan', medication: 'Azithromycin 500mg', frequency: 'Once daily', nextDose: '2026-03-01T10:00:00', status: 'on-time', interactions: [] },
  { id: 'MED-006', patient: 'Mohammed Farhan', medication: 'Salbutamol Nebulization', frequency: 'Every 6 hours', nextDose: '2026-03-01T12:00:00', status: 'on-time', interactions: [] },
  { id: 'MED-007', patient: 'Fatima Begum', medication: 'Levothyroxine 50mcg', frequency: 'Once daily (empty stomach)', nextDose: '2026-03-02T06:00:00', status: 'on-time', interactions: [] },
];

// ─── Admin dashboard (exact reference layout) ───

/** KPI cards: label, value, delta (e.g. "+1.2% last week"), trend (positive|negative), sparkline data */
export const adminDashboardKpis = [
  { id: 'patients', label: 'Patients Today', value: 128, delta: '+1.2% last week', trend: 'positive', sparkData: [118, 122, 120, 125, 124, 128], color: '#38bdf8' },
  { id: 'appointments', label: 'Appointments', value: 42, delta: '+2.0% last week', trend: 'positive', sparkData: [38, 40, 39, 41, 40, 42], color: '#34d399' },
  { id: 'surgeries', label: 'Surgeries', value: 6, delta: '+2.8% last week', trend: 'positive', sparkData: [4, 5, 5, 5, 6, 6], color: '#a78bfa' },
  { id: 'alerts', label: 'Alerts', value: 3, delta: '-1.4% last week', trend: 'negative', sparkData: [4, 3, 4, 3, 3, 3], color: '#f87171' },
];

/** Today's appointments for admin dashboard table: time, patient, doctor, status (Waiting|Completed|Scheduled) */
export const adminTodayAppointments = [
  { id: 1, time: '09:00', patient: 'John Doe', doctor: 'Dr. Smith', status: 'Waiting' },
  { id: 2, time: '10:30', patient: 'Emma Lee', doctor: 'Dr. Alex', status: 'Completed' },
  { id: 3, time: '12:00', patient: 'Mike Ross', doctor: 'Dr. Sam', status: 'Scheduled' },
];

/** Patient & Appointment trends: x-axis labels (e.g. days 16–27), patients series, appointments series */
export const adminTrendsData = {
  labels: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
  patients: [95, 98, 102, 105, 108, 112, 115, 118, 122, 125, 126, 128],
  appointments: [28, 30, 32, 31, 35, 36, 38, 37, 40, 41, 42, 42],
};

/** Mock doctors for admin Doctors page */
export const doctorsList = [
  { id: 'DR-001', name: 'Dr. Priya Sharma', specialization: 'General Medicine', department: 'Internal Medicine', email: 'priya.sharma@hospital.com', status: 'Active' },
  { id: 'DR-002', name: 'Dr. Vikram Mehta', specialization: 'Internal Medicine', department: 'Internal Medicine', email: 'vikram.mehta@hospital.com', status: 'Active' },
  { id: 'DR-003', name: 'Dr. Meena Rao', specialization: 'Cardiology', department: 'Cardiology', email: 'meena.rao@hospital.com', status: 'Active' },
  { id: 'DR-004', name: 'Dr. Vikram Patel', specialization: 'Orthopedics', department: 'Orthopedics', email: 'vikram.patel@hospital.com', status: 'Active' },
  { id: 'DR-005', name: 'Dr. Smith', specialization: 'General Practice', department: 'OPD', email: 'smith@hospital.com', status: 'Active' },
  { id: 'DR-006', name: 'Dr. Alex', specialization: 'Pediatrics', department: 'Pediatrics', email: 'alex@hospital.com', status: 'Active' },
  { id: 'DR-007', name: 'Dr. Sam', specialization: 'General Medicine', department: 'OPD', email: 'sam@hospital.com', status: 'Active' },
];

/** Full appointments list for admin Appointments page */
export const adminAppointmentsList = [
  { id: 1, date: '2026-03-05', time: '09:00', patient: 'John Doe', doctor: 'Dr. Smith', status: 'Waiting', type: 'Consultation' },
  { id: 2, date: '2026-03-05', time: '10:30', patient: 'Emma Lee', doctor: 'Dr. Alex', status: 'Completed', type: 'Follow-up' },
  { id: 3, date: '2026-03-05', time: '12:00', patient: 'Mike Ross', doctor: 'Dr. Sam', status: 'Scheduled', type: 'Consultation' },
  { id: 4, date: '2026-03-05', time: '14:00', patient: 'Rajesh Kumar', doctor: 'Dr. Priya Sharma', status: 'Scheduled', type: 'Lab Review' },
  { id: 5, date: '2026-03-05', time: '15:30', patient: 'Fatima Begum', doctor: 'Dr. Vikram Mehta', status: 'Scheduled', type: 'Consultation' },
  { id: 6, date: '2026-03-06', time: '09:00', patient: 'Lakshmi Devi', doctor: 'Dr. Meena Rao', status: 'Scheduled', type: 'Follow-up' },
  { id: 7, date: '2026-03-06', time: '11:00', patient: 'Ananya Singh', doctor: 'Dr. Priya Sharma', status: 'Scheduled', type: 'Consultation' },
];

/** Recent reports for admin Reports page */
export const adminReportsList = [
  { id: 1, name: 'Daily Census Report', type: 'Operational', date: '2026-03-05', generatedBy: 'Admin Sameer' },
  { id: 2, name: 'OT Utilization Summary', type: 'Analytics', date: '2026-03-04', generatedBy: 'System' },
  { id: 3, name: 'Patient Admissions (Week)', type: 'Clinical', date: '2026-03-03', generatedBy: 'Admin Sameer' },
  { id: 4, name: 'Medication Compliance Report', type: 'Clinical', date: '2026-03-02', generatedBy: 'System' },
  { id: 5, name: 'Alerts & Escalations', type: 'Operational', date: '2026-03-01', generatedBy: 'System' },
];
