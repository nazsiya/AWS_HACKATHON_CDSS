import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPatients } from '../../api/client';
import { isMockMode } from '../../api/config';
import { patients as mockPatients } from '../../data/mockData';
import { useActivity } from '../../context/ActivityContext';
import './Medications.css';

const OPERATIONAL_ALERTS = [
  { id: 1, title: 'Doctor absent', detail: 'You are assigned to manage 6 additional patients.', type: 'Staffing', time: '08:10', action: 'View' },
  { id: 2, title: 'Emergency admission assigned', detail: 'New emergency admission assigned to you.', type: 'Emergency', time: '08:45', action: 'View' },
  { id: 3, title: 'OT rescheduled', detail: 'Knee reconstruction moved to 4:30 PM, OT-3.', type: 'Shift', time: '09:05', action: 'View' },
  { id: 4, title: 'ICU consult requested', detail: 'ICU consult requested for Ward 5 patient.', type: 'Emergency', time: '09:15', action: 'Acknowledge' },
  { id: 5, title: 'Shift extended by 2 hours', detail: 'Overtime approved. Shift end 8:00 PM.', type: 'Shift', time: '09:30', action: 'View' },
  { id: 6, title: 'Nurse escalation', detail: 'Escalation request from Ward 3 (pain management).', type: 'Escalation', time: '09:45', action: 'Acknowledge' },
];

const PENDING_TASKS = [
  { label: 'Review Lab Results', count: 3 },
  { label: 'Sign Discharge Summary', count: 2 },
  { label: 'Approve Prescriptions', count: 5 },
  { label: 'Respond to Nurse Escalation', count: 1 },
  { label: 'Complete Case Notes', count: null },
];

const TODAY_SCHEDULE = [
  { time: '09:00 AM', activity: 'OPD Consultation' },
  { time: '11:00 AM', activity: 'Ward Rounds' },
  { time: '01:30 PM', activity: 'Surgery (Appendectomy)' },
  { time: '04:00 PM', activity: 'ICU Review' },
  { time: '06:00 PM', activity: 'Case Documentation' },
];

function SummaryCard({ label, value, updated }) {
  return (
    <div className="cw-card cw-summary-card">
      <span className="cw-summary-card__dot" aria-hidden />
      <div className="cw-summary-card__value">{value}</div>
      <div className="cw-summary-card__label">{label}</div>
      <div className="cw-summary-card__updated">Updated {updated} mins ago</div>
    </div>
  );
}

function OperationalAlert({ title, detail, type, time, action }) {
  return (
    <div className={`cw-alert cw-alert--${type.toLowerCase()}`}>
      <div className="cw-alert__head">
        <span className="cw-alert__title">{title}</span>
        <span className="cw-alert__type">{type}</span>
      </div>
      <p className="cw-alert__detail">{detail}</p>
      <div className="cw-alert__foot">
        <span className="cw-alert__time">{time}</span>
        <button type="button" className="cw-btn cw-btn--sm">{action}</button>
      </div>
    </div>
  );
}

export default function Medications() {
  const navigate = useNavigate();
  const { logActivity } = useActivity();
  const [list, setList] = useState(isMockMode() ? mockPatients : []);
  const [loading, setLoading] = useState(!isMockMode());
  const [sortBy, setSortBy] = useState('priority'); // priority | name

  useEffect(() => {
    logActivity('view_clinical_workboard');
    if (isMockMode()) return;
    getPatients().then(setList).finally(() => setLoading(false));
  }, [logActivity]);

  const todayPatients = useMemo(() => {
    const dataList = Array.isArray(list) ? list : (list.items || []);
    const filtered = dataList.filter((p) => p.status !== 'scheduled').map((p) => ({
      ...p,
      priority: (p.severity || 'moderate').toLowerCase() === 'critical' ? 'High' : (p.severity || 'moderate').toLowerCase() === 'high' ? 'High' : (p.severity || 'moderate').toLowerCase() === 'moderate' ? 'Medium' : 'Low',
    }));
    if (sortBy === 'priority') {
      const order = { High: 0, Medium: 1, Low: 2 };
      return [...filtered].sort((a, b) => order[a.priority] - order[b.priority]);
    }
    return [...filtered].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }, [list, sortBy]);

  const SUMMARY_CARDS = [
    { label: 'Patients Assigned Today', value: todayPatients.length, updated: '1' },
    { label: 'Critical Cases', value: todayPatients.filter(p => p.priority === 'High').length, updated: '1' },
    { label: 'Pending Notes', value: 5, updated: '3' },
    { label: 'Surgeries Today', value: 3, updated: '1' },
  ];

  const priorityClass = (p) => (p === 'High' ? 'high' : p === 'Medium' ? 'medium' : 'low');

  return (
    <div className="cw-page page-enter">
      <div className="cw-breadcrumb">Doctor Portal / Dashboard / Clinical Workboard</div>
      <h1 className="cw-title">Clinical Workboard</h1>

      <div className="cw-grid">
        {/* 1. Top Summary Strip */}
        <section className="cw-section cw-summary-strip">
          {SUMMARY_CARDS.map((card) => (
            <SummaryCard key={card.label} label={card.label} value={card.value} updated={card.updated} />
          ))}
        </section>

        {/* 2. Primary Work Area - Left 70% */}
        <section className="cw-main">
          {/* A. Today's Patient List */}
          <div className="cw-card cw-patients-card">
            <h2 className="cw-card__title">Today's Patient List</h2>
            <div className="cw-table-wrap">
              <table className="cw-table">
                <thead>
                  <tr>
                    <th>Patient Name</th>
                    <th>Age / Gender</th>
                    <th>Room / OPD</th>
                    <th>Diagnosis</th>
                    <th>
                      <button
                        type="button"
                        className="cw-sort-btn"
                        onClick={() => setSortBy(sortBy === 'priority' ? 'name' : 'priority')}
                      >
                        Priority {sortBy === 'priority' ? '▼' : '▲'}
                      </button>
                    </th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {todayPatients.map((p) => (
                    <tr key={p.id}>
                      <td>{p.name}</td>
                      <td>{p.age != null ? `${p.age}` : '—'} / {(p.gender || '—').slice(0, 1)}</td>
                      <td>{p.ward || 'OPD'}</td>
                      <td>{(Array.isArray(p.conditions) ? p.conditions : [p.conditions]).filter(Boolean).slice(0, 2).join(', ') || '—'}</td>
                      <td>
                        <span className={`cw-priority cw-priority--${priorityClass(p.priority)}`}>{p.priority}</span>
                      </td>
                      <td>
                        <button type="button" className="cw-btn cw-btn--view" onClick={() => navigate(`/patient/${p.id}`)}>View Case</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* B. Pending Clinical Tasks */}
          <div className="cw-card cw-tasks-card">
            <h2 className="cw-card__title">Pending Clinical Tasks</h2>
            <ul className="cw-tasks-list">
              {PENDING_TASKS.map((task) => (
                <li key={task.label} className="cw-tasks-item">
                  <button type="button" className="cw-tasks-link">
                    {task.label}
                    {task.count != null && <span className="cw-tasks-count">({task.count})</span>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 3. Right 30% - Operational Alert Center */}
        <aside className="cw-sidebar">
          <div className="cw-card cw-alerts-card">
            <h2 className="cw-card__title">Operational Alert Center</h2>
            <div className="cw-alerts-list">
              {OPERATIONAL_ALERTS.map((a) => (
                <OperationalAlert
                  key={a.id}
                  title={a.title}
                  detail={a.detail}
                  type={a.type}
                  time={a.time}
                  action={a.action}
                />
              ))}
            </div>
          </div>
        </aside>

        {/* 4. Today's Schedule Panel - full width */}
        <section className="cw-section cw-schedule-section">
          <div className="cw-card cw-schedule-card">
            <h2 className="cw-card__title">Today's Schedule</h2>
            <div className="cw-schedule-timeline">
              {TODAY_SCHEDULE.map((slot) => (
                <div key={slot.time} className="cw-schedule-item">
                  <span className="cw-schedule__time">{slot.time}</span>
                  <span className="cw-schedule__dash">–</span>
                  <span className="cw-schedule__activity">{slot.activity}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
