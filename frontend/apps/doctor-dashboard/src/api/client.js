/**
 * CDSS REST API client.
 * Sends Authorization: Bearer <token> when getToken is provided.
 * Use with VITE_USE_MOCK=true for mock data in components; when false, these calls hit the backend.
 */

import { config } from './config.js';

let getToken = () => null;

export function setAuthTokenGetter(fn) {
  getToken = fn;
}

async function request(method, path, body = null) {
  const url = `${config.apiUrl}${path}`;
  const headers = {
    'Content-Type': 'application/json',
  };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (config.apiKey) {
    headers['x-api-key'] = config.apiKey;
  }
  const options = { method, headers };
  if (body != null && method !== 'GET') {
    options.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    const isNetworkError =
      (err && err.message === 'Failed to fetch') ||
      (err && typeof err.message === 'string' && err.message.includes('NetworkError'));
    const msg = isNetworkError
      ? `Cannot reach API at ${config.apiUrl || '(not set)'}. Ensure the backend is running (e.g. run: python scripts/run_api_local.py) and VITE_API_URL in .env.local is correct.`
      : (err?.message || 'Network error');
    throw new Error(msg);
  }
  if (!res.ok) {
    const text = await res.text();
    let errBody;
    try {
      errBody = JSON.parse(text);
    } catch {
      errBody = { message: text || res.statusText };
    }
    throw new Error(errBody.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get(path) {
    return request('GET', path);
  },
  post(path, body) {
    return request('POST', path, body);
  },
  put(path, body) {
    return request('PUT', path, body);
  },
  delete(path) {
    return request('DELETE', path);
  },
};

// Convenience methods aligned with backend routes

export function getDashboard(doctorId = '') {
  const qs = doctorId ? `?doctor_id=${encodeURIComponent(doctorId)}` : '';
  return api.get(`/dashboard${qs}`);
}

export function getPatients() {
  return api.get('/api/v1/patients');
}

export function getPatient(patientId) {
  return api.get(`/api/v1/patients/${patientId}`);
}

export function startConsultation(patientId, doctorId) {
  return api.post('/api/v1/consultations/start', { patient_id: patientId, doctor_id: doctorId });
}

export function saveConsultation(patientId, body) {
  return api.post('/api/v1/consultations', { patient_id: patientId, ...body });
}

export function postAgent(body) {
  return api.post('/agent', body);
}

/** POST /api/ai/summarize – summarize text or conversation; returns { summary, safety_disclaimer }. */
export function postSummarize(body) {
  return api.post('/api/ai/summarize', body).catch(() => api.post('/api/v1/ai/summarize', body));
}

export function getMedications() {
  return api.get('/api/v1/medications');
}

export function getSurgeries() {
  return api.get('/api/v1/surgeries');
}

export function getSurgery(surgeryId) {
  return api.get(`/api/v1/surgeries/${surgeryId}`);
}

/** POST /api/v1/surgeries/:id/analyse – get AI-generated checklist and required instruments for the surgery. */
export function analyseSurgery(surgeryId) {
  return api.post(`/api/v1/surgeries/${surgeryId}/analyse`, {});
}

export function getResources() {
  return api.get('/api/v1/resources');
}

export function getSchedule() {
  return api.get('/api/v1/schedule');
}

export function sendNudge(patientId, medicationId) {
  return api.post('/api/v1/reminders/nudge', { patient_id: patientId, medication_id: medicationId });
}

export function scheduleReminder(patientId, medicationId, scheduledAt) {
  return api.post('/api/v1/reminders', { patient_id: patientId, medication_id: medicationId, scheduled_at: scheduledAt });
}

// Admin APIs (Phase 10)
export function getUsers() {
  return api.get('/api/v1/admin/users');
}

export function getAuditLog(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/api/v1/admin/audit${qs ? `?${qs}` : ''}`);
}

/** Doctor_ID-linked activity log (Criteria 4). Backend may expose POST /api/v1/activity */
export function postActivityLog(body) {
  return api.post('/api/v1/activity', body).catch(() => null);
}

export function getSystemConfig() {
  return api.get('/api/v1/admin/config');
}

export function updateSystemConfig(body) {
  return api.put('/api/v1/admin/config', body);
}

export function getAnalytics() {
  return api.get('/api/v1/admin/analytics');
}

// Appointments
export function getAppointments() {
  return api.get('/api/v1/appointments');
}

export function createAppointment(body) {
  return api.post('/api/v1/appointments', body);
}

// Tasks
export function getTasks() {
  return api.get('/api/v1/tasks');
}

// AI Agent endpoints
export function postAiPrescription(body) {
  return api.post('/api/ai/prescription', body);
}

export function postAiAdherence(body) {
  return api.post('/api/ai/adherence', body);
}

export function postAiEngagement(body) {
  return api.post('/api/ai/engagement', body);
}

export function postAiResources(body) {
  return api.post('/api/ai/resources', body);
}
