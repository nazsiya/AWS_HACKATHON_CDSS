/**
 * Doctor_ID-linked activity history (Acceptance Criteria 4).
 * Logs healthcare provider actions for audit and "My Activity" display.
 * Patient_ID is recorded when action relates to a specific patient (Criteria 5).
 */

import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { isMockMode } from '../api/config';
import * as api from '../api/client';

const ACTIVITY_STORAGE_KEY = 'cdss_doctor_activity';
const MAX_STORED = 200;

const ActivityContext = createContext();

function loadStoredActivities(doctorId) {
  try {
    const raw = localStorage.getItem(ACTIVITY_STORAGE_KEY);
    if (!raw) return [];
    const all = JSON.parse(raw);
    return Array.isArray(all) ? all.filter((a) => a.doctorId === doctorId).slice(-MAX_STORED) : [];
  } catch {
    return [];
  }
}

function saveActivities(activities) {
  try {
    localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activities.slice(-MAX_STORED)));
  } catch (_) { /* ignore */ }
}

export function ActivityProvider({ children }) {
  const { user } = useAuth();
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    if (!user?.id) {
      setActivities([]);
      return;
    }
    setActivities(loadStoredActivities(user.id));
  }, [user?.id]);

  const logActivity = useCallback(
    async (type, options = {}) => {
      const { patientId = null, resource = null, detail = null } = options;
      const doctorId = user?.id;
      if (!doctorId) return;

      const entry = {
        id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        doctorId,
        doctorName: user?.name || 'Unknown',
        type,
        patientId: patientId || undefined,
        resource: resource || undefined,
        detail: detail || undefined,
        timestamp: new Date().toISOString(),
      };

      setActivities((prev) => {
        const next = [...prev, entry].slice(-MAX_STORED);
        saveActivities(next);
        return next;
      });

      if (!isMockMode() && typeof api.postActivityLog === 'function') {
        try {
          await api.postActivityLog({
            doctor_id: doctorId,
            action: type,
            patient_id: patientId || undefined,
            resource: resource || undefined,
            detail: detail || undefined,
          });
        } catch (_) {
          /* best-effort; local list already updated */
        }
      }
    },
    [user?.id, user?.name]
  );

  const recentActivity = activities
    .filter((a) => a.doctorId === user?.id)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 50);

  return (
    <ActivityContext.Provider value={{ logActivity, recentActivity, activities }}>
      {children}
    </ActivityContext.Provider>
  );
}

export const useActivity = () => useContext(ActivityContext);
