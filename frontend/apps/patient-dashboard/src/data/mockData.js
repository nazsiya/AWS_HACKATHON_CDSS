// Mock patient data for the Patient Portal (matches logged-in user id 'p1')

export const patients = [
  {
    id: 'p1',
    name: 'Rahul Kumar',
    email: 'patient@cdss.ai',
    age: 42,
    gender: 'Male',
    bloodGroup: 'B+',
    contact: '+91 98765 43210',
    lastVisit: '2026-02-28',
    nextAppointment: '2026-03-01T10:30:00',
    nextAppointmentDetails: {
      doctorName: 'Dr. Vikram Mehta',
      department: 'Internal Medicine',
      notes: 'Follow-up for BP and glucose review',
    },
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
            hi: 'आपका रक्तचाप थोड़ा अधिक था और शुगर नियंत्रण में सुधार की जरूरत है।',
            ta: 'உங்கள் இரத்த அழுத்தம் சிறிது அதிகமாக இருந்தது; சர்க்கரை கட்டுப்பாட்டில் மேம்பாடு தேவை.',
          },
          reasoning: {
            en: 'The medication dose was increased to improve blood pressure control while keeping your diabetes medicines unchanged for now.',
            hi: 'रक्तचाप को बेहतर नियंत्रित करने के लिए दवा की खुराक बढ़ाई गई।',
            ta: 'இரத்த அழுத்தக் கட்டுப்பாட்டை மேம்படுத்த மருந்தளவு உயர்த்தப்பட்டது.',
          },
          tips: {
            en: ['Take medicines at the same time daily.', 'Limit salt and sugary foods.', 'Walk 20–30 minutes most days (if safe for you).'],
            hi: ['दवाएँ रोज़ एक ही समय पर लें।', 'नमक और मीठे खाद्य पदार्थ सीमित करें।'],
            ta: ['மருந்துகளை தினமும் ஒரே நேரத்தில் எடுத்துக் கொள்ளுங்கள்.', 'உப்பு மற்றும் சர்க்கரை குறைக்கவும்.'],
          },
          cautions: {
            en: ['Seek care urgently if you have chest pain, severe breathlessness, or fainting.', 'Report dizziness or swelling after the dose change.'],
            hi: ['सीने में दर्द हो तो तुरंत चिकित्सा लें।'],
            ta: ['மார்பு வலி இருந்தால் உடனடி மருத்துவ உதவி பெறுங்கள்.'],
          },
        },
      },
      todayMedications: [
        { id: 'dose-p1-1', medicine: 'Metformin', dosage: '500mg Tab', time: '08:00', status: 'Taken' },
        { id: 'dose-p1-2', medicine: 'Metformin', dosage: '500mg Tab', time: '20:00', status: 'Pending' },
        { id: 'dose-p1-3', medicine: 'Amlodipine', dosage: '10mg Tab', time: '09:00', status: 'Missed' },
      ],
      appointments: {
        upcoming: [
          { id: 'apt-p1-1', doctorName: 'Dr. Vikram Mehta', department: 'Internal Medicine', dateTime: '2026-03-01T10:30:00', clinicalNotes: 'BP + HbA1c review' },
          { id: 'apt-p1-2', doctorName: 'Dr. Priya Sharma', department: 'General Medicine', dateTime: '2026-03-08T09:30:00', clinicalNotes: 'Medication adherence follow-up' },
        ],
        past: [
          { id: 'visit-p1-1', doctorName: 'Dr. Priya Sharma', department: 'Internal Medicine', dateTime: '2026-02-28T10:00:00', summaryAvailable: true },
          { id: 'visit-p1-2', doctorName: 'Dr. Priya Sharma', department: 'Internal Medicine', dateTime: '2026-02-15T10:00:00', summaryAvailable: true },
        ],
      },
    },
  },
];

// For PatientPortalHistory (copied from doctor-dashboard); not used in current routes
export const consultationHistory = [
  { id: 'ch1', patientId: 'p1', date: '2026-02-28', doctor: 'Dr. Priya Sharma', aiSummary: 'Follow-up for BP and glucose.' },
];
