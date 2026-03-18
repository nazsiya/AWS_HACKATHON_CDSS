import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getAppointments } from '../../api/client';
import { adminAppointmentsList } from '../../data/mockData';
import './Appointments.css';

const statusColors = { Waiting: '#3b82f6', Completed: '#22c55e', Scheduled: '#eab308', Cancelled: '#94a3b8' };

export default function Appointments() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isMockMode()) {
      setAppointments(adminAppointmentsList);
      setLoading(false);
      return;
    }
    let cancelled = false;
    getAppointments()
      .then((res) => {
        if (cancelled) return;
        const items = res?.appointments || [];
        setAppointments(items);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setAppointments([]);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const filtered = appointments.filter((apt) => {
    const matchSearch =
      !search ||
      (apt.patient || '').toLowerCase().includes(search.toLowerCase()) ||
      (apt.doctor || '').toLowerCase().includes(search.toLowerCase()) ||
      (apt.type || '').toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || (apt.status || '').toLowerCase() === statusFilter;
    const matchDateFrom = !dateFrom || (apt.date || '') >= dateFrom;
    const matchDateTo = !dateTo || (apt.date || '') <= dateTo;
    return matchSearch && matchStatus && matchDateFrom && matchDateTo;
  });

  if (loading) {
    return (
      <div className="appointments-page page-enter">
        <p style={{ textAlign: 'center', padding: '2rem' }}>Loading appointments...</p>
      </div>
    );
  }

  return (
    <div className="appointments-page page-enter">
      <div className="appointments-page__header">
        <h1 className="appointments-page__title">Appointments</h1>
        <p className="appointments-page__desc">View and manage all appointments.</p>
      </div>

      <div className="appointments-page__toolbar">
        <label className="appointments-page__search-wrap">
          <span className="appointments-page__search-icon" aria-hidden>🔍</span>
          <input
            type="search"
            className="appointments-page__search"
            placeholder="Search by patient, doctor, or type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search appointments"
          />
        </label>
        <div className="appointments-page__filters">
          <input
            type="date"
            className="appointments-page__date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            aria-label="From date"
          />
          <input
            type="date"
            className="appointments-page__date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            aria-label="To date"
          />
          <button
            type="button"
            className={`appointments-page__filter-btn ${statusFilter === 'all' ? 'active' : ''}`}
            onClick={() => setStatusFilter('all')}
          >
            All
          </button>
          <button
            type="button"
            className={`appointments-page__filter-btn ${statusFilter === 'scheduled' ? 'active' : ''}`}
            onClick={() => setStatusFilter('scheduled')}
          >
            Scheduled
          </button>
          <button
            type="button"
            className={`appointments-page__filter-btn ${statusFilter === 'waiting' ? 'active' : ''}`}
            onClick={() => setStatusFilter('waiting')}
          >
            Waiting
          </button>
          <button
            type="button"
            className={`appointments-page__filter-btn ${statusFilter === 'completed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('completed')}
          >
            Completed
          </button>
        </div>
      </div>

      <div className="appointments-page__card">
        <table className="appointments-page__table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Time</th>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Type</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="appointments-page__empty">No appointments match your filters.</td>
              </tr>
            ) : (
              filtered.map((apt) => (
                <tr key={apt.id}>
                  <td>{apt.date}</td>
                  <td>{apt.time}</td>
                  <td className="appointments-page__name">{apt.patient}</td>
                  <td>{apt.doctor}</td>
                  <td>{apt.type}</td>
                  <td>
                    <span
                      className="appointments-page__status"
                      style={{ ['--status-color']: statusColors[apt.status] || '#94a3b8' }}
                    >
                      <span className="appointments-page__status-dot" /> {apt.status}
                    </span>
                  </td>
                  <td>
                    <button type="button" className="appointments-page__action">View</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
