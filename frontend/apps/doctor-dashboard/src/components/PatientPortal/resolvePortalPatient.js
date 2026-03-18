import { patients } from '../../data/mockData';

function isoInDays(days) {
  const now = Date.now();
  return new Date(now + days * 24 * 60 * 60 * 1000).toISOString();
}

function deepClone(value) {
  // Mock data is plain JSON; this is enough and avoids extra deps.
  return JSON.parse(JSON.stringify(value));
}

function buildStubPatientFromTemplate(template, user) {
  const u = user || {};
  const stub = deepClone(template || {});

  const safeId = u.id || `PT-DEMO-${String(Math.random()).slice(2, 8)}`;
  const safeName = u.name || 'Demo Patient';
  const safeEmail = u.email || '';

  stub.id = safeId;
  stub.name = safeName;
  stub.email = safeEmail;

  stub.portal = stub.portal || {};
  stub.portal.preferredLanguage = stub.portal.preferredLanguage || 'en';
  stub.portal.activePrescriptionsCount = stub.portal.activePrescriptionsCount ?? 2;
  stub.portal.medicationAdherenceStatus = stub.portal.medicationAdherenceStatus || 'Good compliance';
  stub.portal.weeklyAdherence = stub.portal.weeklyAdherence ?? 0.86;

  // Appointments: keep a predictable schedule relative to "now"
  stub.nextAppointment = isoInDays(2);
  stub.nextAppointmentDetails = stub.nextAppointmentDetails || {};
  stub.nextAppointmentDetails.doctorName = stub.nextAppointmentDetails.doctorName || 'Dr. Priya Sharma';
  stub.nextAppointmentDetails.department = stub.nextAppointmentDetails.department || 'General Medicine';
  stub.nextAppointmentDetails.notes = stub.nextAppointmentDetails.notes || 'Follow-up review (demo data)';

  stub.portal.appointments = stub.portal.appointments || {};
  stub.portal.appointments.upcoming = [
    {
      id: `apt-${safeId}-1`,
      doctorName: 'Dr. Priya Sharma',
      department: 'General Medicine',
      dateTime: isoInDays(2),
      clinicalNotes: 'Vitals review + medication adherence (demo)',
    },
    {
      id: `apt-${safeId}-2`,
      doctorName: 'Dr. Vikram Mehta',
      department: 'Internal Medicine',
      dateTime: isoInDays(9),
      clinicalNotes: 'Lab review and lifestyle plan (demo)',
    },
  ];
  stub.portal.appointments.past = [
    {
      id: `visit-${safeId}-1`,
      doctorName: 'Dr. Vikram Mehta',
      department: 'Internal Medicine',
      dateTime: isoInDays(-10),
      summaryAvailable: true,
    },
    {
      id: `visit-${safeId}-2`,
      doctorName: 'Dr. Priya Sharma',
      department: 'General Medicine',
      dateTime: isoInDays(-28),
      summaryAvailable: true,
    },
  ];

  // Today's meds (demo)
  stub.portal.todayMedications = [
    { id: `dose-${safeId}-1`, medicine: 'Metformin', dosage: '500mg Tab', time: '08:00', status: 'Taken' },
    { id: `dose-${safeId}-2`, medicine: 'Metformin', dosage: '500mg Tab', time: '20:00', status: 'Pending' },
    { id: `dose-${safeId}-3`, medicine: 'Amlodipine', dosage: '10mg Tab', time: '09:00', status: 'Missed' },
  ];

  // AI visit summary (demo)
  stub.portal.aiVisitSummary = stub.portal.aiVisitSummary || {};
  stub.portal.aiVisitSummary.available = true;
  stub.portal.aiVisitSummary.agentName = stub.portal.aiVisitSummary.agentName || 'MedAI Summary Agent';
  stub.portal.aiVisitSummary.lastVisitDate = stub.portal.aiVisitSummary.lastVisitDate || new Date(isoInDays(-10)).toISOString().slice(0, 10);
  stub.portal.aiVisitSummary.treatingPhysician = stub.portal.aiVisitSummary.treatingPhysician || 'Dr. Vikram Mehta';
  stub.portal.aiVisitSummary.sections = stub.portal.aiVisitSummary.sections || {
    abstract: {
      en: 'This is a demo summary of your last visit. It is for testing only and not medical advice.',
      hi: 'यह आपकी पिछली विज़िट का डेमो सारांश है। यह केवल परीक्षण के लिए है और चिकित्सीय सलाह नहीं है।',
      ta: 'இது உங்கள் கடைசி விஜிட்டின் டெமோ சுருக்கம். இது சோதனைக்காக மட்டுமே; மருத்துவ ஆலோசனை அல்ல.',
    },
    reasoning: {
      en: 'Recommendations are generated from stub data. Always confirm with your clinician.',
      hi: 'सिफारिशें स्टब डेटा से बनाई गई हैं। कृपया अपने डॉक्टर से पुष्टि करें।',
      ta: 'பரிந்துரைகள் டெமோ தரவிலிருந்து உருவாக்கப்பட்டவை. மருத்துவரிடம் உறுதி செய்யவும்.',
    },
    tips: {
      en: ['Take medicines at the same time daily.', 'Limit salt and sugary foods.', 'Walk 20–30 minutes most days (if safe for you).'],
      hi: ['दवाएँ रोज़ एक ही समय पर लें।', 'नमक और मीठे खाद्य पदार्थ सीमित करें।', '20–30 मिनट टहलें (यदि सुरक्षित हो)।'],
      ta: ['மருந்துகளை தினமும் ஒரே நேரத்தில் எடுத்துக் கொள்ளுங்கள்.', 'உப்பு/சர்க்கரையை குறைக்கவும்.', '20–30 நிமிடம் நடை (பாதுகாப்பானால்).'],
    },
    cautions: {
      en: ['Seek urgent care for chest pain, severe breathlessness, fainting, or stroke symptoms.'],
      hi: ['सीने में दर्द/तेज़ सांस फूलना/बेहोशी हो तो तुरंत चिकित्सा लें।'],
      ta: ['மார்பு வலி/கடுமையான மூச்சுத்திணறல்/மயக்கம் இருந்தால் உடனடி மருத்துவ உதவி பெறுங்கள்.'],
    },
  };

  // Pre-op checklist (demo stub data)
  stub.portal.preOpChecklist = {
    surgery: 'Elective procedure (demo)',
    scheduledDateTime: isoInDays(14),
    checklist: [
      { name: 'Fasting (NPO) instructions understood', checked: true },
      { name: 'Medication list reviewed (including blood thinners)', checked: false },
      { name: 'Allergies confirmed', checked: true },
      { name: 'Consent process completed', checked: false },
      { name: 'Arrange escort / post-op transport', checked: false },
    ],
    disclaimer:
      'Demo checklist for UI only. Always follow your hospital’s instructions and your clinician’s advice.',
  };

  return stub;
}

/**
 * Resolve a patient record for a logged-in portal user.
 *
 * - First tries to match existing mock patients by id.
 * - If not found (common for Cognito users where id is a UUID/sub),
 *   returns a stub patient record with populated demo data.
 */
export function resolvePortalPatient(user) {
  const userId = user?.id;
  if (userId) {
    const found = patients.find((p) => p.id === userId);
    if (found) return found;
  }

  const template = patients.find((p) => p?.portal) || patients[0] || null;
  if (!template) return null;
  return buildStubPatientFromTemplate(template, user);
}

