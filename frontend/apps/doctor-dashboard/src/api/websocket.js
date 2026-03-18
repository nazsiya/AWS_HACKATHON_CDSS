/**
 * WebSocket client for CDSS real-time updates (e.g. surgical events, patient vitals).
 * Connects to VITE_WS_URL; use subscribe_patient or subscribe_surgery when backend supports it.
 */

import { config } from './config.js';

let ws = null;
let reconnectTimer = null;
const listeners = new Set();

function getWsUrl() {
  const base = config.wsUrl;
  if (!base) return null;
  const url = base.startsWith('ws') ? base : `wss://${base.replace(/^https?:\/\//, '')}`;
  return url;
}

function notify(msg) {
  try {
    const data = typeof msg === 'string' ? JSON.parse(msg) : msg;
    listeners.forEach((fn) => fn(data));
  } catch (_) {
    listeners.forEach((fn) => fn({ type: 'message', raw: msg }));
  }
}

export function connectWs(options = {}) {
  const url = getWsUrl();
  if (!url) return null;
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return ws;
  }
  const doctorId = options.doctorId || '';
  const fullUrl = doctorId ? `${url}?doctor_id=${encodeURIComponent(doctorId)}` : url;
  ws = new WebSocket(fullUrl);

  ws.onopen = () => {
    if (options.onOpen) options.onOpen();
  };
  ws.onmessage = (event) => notify(event.data);
  ws.onerror = (e) => {
    if (options.onError) options.onError(e);
  };
  ws.onclose = () => {
    ws = null;
    if (options.onClose) options.onClose();
    if (options.reconnect !== false && getWsUrl()) {
      reconnectTimer = setTimeout(() => connectWs(options), 3000);
    }
  };
  return ws;
}

export function disconnectWs() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
}

export function subscribePatient(patientId) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: 'subscribe_patient', patient_id: patientId }));
}

export function subscribeSurgery(surgeryId) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ action: 'subscribe_surgery', surgery_id: surgeryId }));
}

export function addWsListener(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function isWsEnabled() {
  return !!getWsUrl();
}
