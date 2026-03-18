import { useState, useEffect } from 'react';
import Calendar from 'react-calendar';
import { useAuth, roles } from '../../context/AuthContext';
import { isMockMode } from '../../api/config';
import { getSchedule, getSurgeries } from '../../api/client';
import { todaySchedule, surgeries as mockSurgeries } from '../../data/mockData';
import { useNavigate } from 'react-router-dom';
import 'react-calendar/dist/Calendar.css';
import './Schedule.css';

export default function Schedule() {
  const { hasRole } = useAuth();
  const navigate = useNavigate();
  const isSurgeon = hasRole(roles.SURGEON);
  const [date, setDate] = useState(new Date());
  const [scheduleData, setScheduleData] = useState([]);
  const [surgeriesData, setSurgeriesData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isMockMode()) {
      setScheduleData(todaySchedule);
      setSurgeriesData(mockSurgeries);
      setLoading(false);
      return;
    }
    let cancelled = false;
    Promise.all([
      getSchedule().catch(() => ({ schedule: [] })),
      getSurgeries().catch(() => ({ surgeries: [] })),
    ]).then(([schedRes, surgRes]) => {
      if (cancelled) return;
      const slots = schedRes?.schedule || schedRes?.items || [];
      setScheduleData(slots.length > 0 ? slots.map((s) => ({
        time: s.slot_time || s.time || '09:00',
        patient: s.patient_name || s.patient || '—',
        type: s.surgery_type || s.type || 'Consultation',
        status: s.status || 'upcoming',
        location: s.ot_id || s.ot || s.location || '—',
        consultationType: s.surgery_type || s.type || 'Consultation',
        date: s.date,
      })) : []);
      const surgs = surgRes?.surgeries || surgRes?.items || [];
      setSurgeriesData(surgs.length > 0 ? surgs : []);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  // Format date for comparison and display
  const selectedDateStr = date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });

  const isToday = (someDate) => {
    const today = new Date();
    return someDate.getDate() === today.getDate() &&
      someDate.getMonth() === today.getMonth() &&
      someDate.getFullYear() === today.getFullYear();
  };

  // Helper to get appointments for a specific date (filter by date when using API data)
  const getAppointmentsForDate = (selectedDate) => {
    const targetDateStr = selectedDate.toISOString().slice(0, 10);
    if (isMockMode()) {
      if (isToday(selectedDate)) {
        return scheduleData.map((s) => ({
          ...s,
          location: s.location || (s.type === 'Pre-op Check' ? 'OT-3' : 'Room 4'),
          consultationType: s.consultationType || s.type,
        }));
      }
      const day = selectedDate.getDay();
      if (day === 0) return [];
      return scheduleData.slice(0, (day % 4) + 2).map((s, i) => ({
        ...s,
        time: `${9 + i}:00`,
        location: 'Room 4',
        consultationType: s.consultationType || s.type,
      }));
    }
    return scheduleData.filter((s) => (s.date || '').slice(0, 10) === targetDateStr).map((s) => ({
      ...s,
      location: s.location || s.ot || '—',
      consultationType: s.consultationType || s.type,
    }));
  };

  const currentAppointments = getAppointmentsForDate(date);
  const otSchedule = isSurgeon ? surgeriesData.filter((s) => s.status === 'scheduled' || s.status === 'pre-op') : [];

  if (loading) {
    return (
      <div className="schedule-page page-enter">
        <div className="schedule-container">
          <p style={{ textAlign: 'center', padding: '2rem' }}>Loading schedule...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="schedule-page page-enter">
      <div className="schedule-container">
        <div className="schedule__header text-center">
          <h1 className="schedule-page__title">Appointments & Schedule</h1>
          <p className="schedule-page__subtitle">Select a date to view your clinical schedule</p>
        </div>

        <div className="schedule-vertical-stack">
          {/* Calendar at the top */}
          <section className="schedule-card calendar-card centered-card">
            <h2 className="schedule-card__title">Select Date</h2>
            <div className="calendar-container">
              <Calendar
                onChange={setDate}
                value={date}
                className="custom-calendar"
              />
            </div>
          </section>

          {/* Appointments for selected date */}
          <section className="schedule-card appointments-card centered-card">
            <div className="schedule-card__header">
              <h2 className="schedule-card__title">
                {isToday(date) ? "Today's Appointments" : `Appointments for ${selectedDateStr}`}
              </h2>
              <span className="schedule-card__count">{currentAppointments.length} items</span>
            </div>

            {currentAppointments.length > 0 ? (
              <ul className="schedule-list">
                {currentAppointments.map((item, i) => (
                  <li key={i} className={`schedule-list__item schedule-list__item--${item.status}`}>
                    <div className="schedule-item__main">
                      <span className="schedule-list__time">{item.time}</span>
                      <span className="schedule-list__patient">{item.patient}</span>
                    </div>
                    <div className="schedule-item__meta">
                      <span className="schedule-list__type">{item.consultationType}</span>
                      <span className="schedule-list__location">{item.location}</span>
                    </div>
                    <div className="schedule-item__actions">
                      <button type="button" className="schedule-list__btn" onClick={() => item.patient && navigate('/patients')}>
                        View Details
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <p>No appointments scheduled for this date.</p>
              </div>
            )}
          </section>

          {/* OT Schedule at the bottom if applicable */}
          {isSurgeon && (
            <section className="schedule-card ot-card centered-card">
              <h2 className="schedule-card__title">OT Schedule</h2>
              <ul className="schedule-list">
                {otSchedule.map((s) => (
                  <li key={s.id} className="schedule-list__item">
                    <div className="schedule-item__main">
                      <span className="schedule-list__time">{s.time}</span>
                      <span className="schedule-list__patient">{s.patient}</span>
                    </div>
                    <div className="schedule-item__meta">
                      <span className="schedule-list__type">{s.type}</span>
                      <span className="schedule-list__location">{s.ot}</span>
                    </div>
                    <button type="button" className="schedule-list__btn" onClick={() => navigate('/surgery')}>
                      View
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
