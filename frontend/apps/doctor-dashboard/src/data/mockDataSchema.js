/**
 * All mock data and API response field schemas used by the frontend.
 * Single source of field names and shapes (no documentation).
 */

// ─── mockData.js exports ───────────────────────────────────────────────────

export const currentDoctorSchema = {
  id: 'string',
  name: 'string',
  specialization: 'string',
  department: 'string',
  avatar: 'string | null',
  initials: 'string',
};

export const patientSchema = {
  id: 'string',
  name: 'string',
  age: 'number',
  gender: 'string',
  bloodGroup: 'string',
  contact: 'string',
  abdmId: 'string',
  ward: 'string',
  severity: 'string', // low | moderate | high | critical
  vitals: { hr: 'number', bp: 'string', spo2: 'number', temp: 'number' },
  conditions: 'string[]',
  lastVisit: 'string', // date
  nextAppointment: 'string | null', // ISO datetime
  nextAppointmentDetails: {
    doctorName: 'string',
    department: 'string',
    notes: 'string',
  },
  status: 'string', // waiting | in-consultation | scheduled
  adherence: 'number',
  portal: {
    preferredLanguage: 'string',
    activePrescriptionsCount: 'number',
    medicationAdherenceStatus: 'string',
    weeklyAdherence: 'number',
    aiVisitSummary: {
      available: 'boolean',
      agentName: 'string',
      lastVisitDate: 'string',
      treatingPhysician: 'string',
      sections: {
        abstract: 'string | object', // en/hi/ta or string
        reasoning: 'string | object',
        tips: 'string[] | object',
        cautions: 'string[] | object',
      },
    },
    todayMedications: [
      { id: 'string', medicine: 'string', dosage: 'string', time: 'string', status: 'string' },
    ],
    appointments: {
      upcoming: [
        { id: 'string', doctorName: 'string', department: 'string', dateTime: 'string', clinicalNotes: 'string' },
      ],
      past: [
        { id: 'string', doctorName: 'string', department: 'string', dateTime: 'string', summaryAvailable: 'boolean' },
      ],
    },
  },
  surgeryReadiness: {
    preOpStatus: 'string',
    riskFactors: 'string[]',
    lastAssessed: 'string',
  },
};

export const todayScheduleSchema = [
  { time: 'string', patient: 'string', type: 'string', status: 'string' },
];

export const aiAlertSchema = {
  id: 'string',
  type: 'string',
  title: 'string',
  message: 'string',
  patient: 'string',
  time: 'string',
};

export const clinicalUpdateSchema = {
  id: 'string',
  type: 'string',
  title: 'string',
  patientName: 'string',
  description: 'string',
  time: 'string',
  priority: 'string',
};

export const consultationHistorySchema = {
  id: 'string',
  patientId: 'string',
  date: 'string',
  doctor: 'string',
  notes: 'string',
  aiSummary: 'string',
  prescriptions: [
    { medication: 'string', dosage: 'string', frequency: 'string', duration: 'string' },
  ],
};

export const surgerySchema = {
  id: 'string',
  patient: 'string',
  type: 'string',
  complexity: 'string',
  estimatedDuration: 'string',
  ot: 'string',
  date: 'string',
  time: 'string',
  status: 'string', // scheduled | pre-op | in-prep
  surgeon: 'string',
};

export const medicationSchema = {
  id: 'string',
  patient: 'string',
  medication: 'string',
  frequency: 'string',
  nextDose: 'string', // ISO datetime
  status: 'string', // on-time | overdue | given
  interactions: 'string[]',
};

// ─── Admin / inline mocks ──────────────────────────────────────────────────

export const mockUsersSchema = [
  { id: 'string', name: 'string', email: 'string', role: 'string', status: 'string' },
];

export const mockAuditSchema = [
  { id: 'number', user_id: 'string', user_email: 'string', action: 'string', resource: 'string', timestamp: 'string' },
];

export const mockResourcesSchema = {
  ots: [{ id: 'string', name: 'string', status: 'string', nextFree: 'string | null' }],
  equipment: [{ id: 'string', name: 'string', status: 'string', location: 'string' }],
  staff: [{ id: 'string', name: 'string', specialty: 'string', status: 'string' }],
};

export const mockConfigSchema = {
  mcpHospitalEndpoint: 'string',
  mcpAbdmEndpoint: 'string',
  featureFlags: { aiAssist: 'boolean', voiceInput: 'boolean' },
};

export const mockAnalyticsSchema = {
  otUtilization: [{ ot: 'string', percent: 'number' }],
  otRecommendations: 'string',
  otConflicts: [
    { id: 'string', ot: 'string', date: 'string', time: 'string', message: 'string' },
  ],
  agentUsage: [{ agent: 'string', calls: 'number' }],
  reminderStats: { sent: 'number', acknowledged: 'number', overdue: 'number' },
};

export const mockCapacitySchema = { staff: 'number', assets: 'number' };

export const mockCategoriesSchema = [
  { id: 'string', label: 'string', icon: 'string' },
];

export const mockInventorySchema = [
  { id: 'string', name: 'string', specialty: 'string', status: 'string', assignedTo: 'string', area: 'string' },
];

export const mockReplacementsSchema = [
  { id: 'string', name: 'string', specialty: 'string', status: 'string' },
];

export const mockRecommendationSchema = {
  id: 'number',
  title: 'string',
  detail: 'string',
  type: 'string',
};

export const mockAgentSchema = { name: 'string', status: 'string' };

// ─── API response shapes (when not mock) ────────────────────────────────────

export const apiDashboardSchema = {
  stats: [{ label: 'string', value: 'number', trend: 'string', type: 'string' }],
  patient_queue: [
    { id: 'string', name: 'string', status: 'string', vitals: 'object', severity: 'string' },
  ],
  ai_alerts: [{ id: 'string', type: 'string', message: 'string', time: 'string' }],
};

export const apiScheduleSchema = {
  schedule: [{ time: 'string', patient: 'string', type: 'string', status: 'string' }],
};

export const apiQueueItemSchema = {
  id: 'string',
  name: 'string',
  gender: 'string',
  ward: 'string',
  conditions: 'string[]',
  vitals: 'object',
  severity: 'string',
  status: 'string',
};
