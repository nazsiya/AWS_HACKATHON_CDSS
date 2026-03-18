import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getAnalytics } from '../../api/client';
import '../Settings/AdminShared.css';

const mockAnalytics = {
  otUtilization: [{ ot: 'OT-1', percent: 78 }, { ot: 'OT-2', percent: 45 }, { ot: 'OT-3', percent: 90 }],
  otRecommendations: 'OT-2 underutilized (45%). Consider moving elective cases from OT-1 to balance load. OT-3 at 90% — monitor for overrun.',
  otConflicts: [
    { id: 'c1', ot: 'OT-1', date: '2026-03-05', time: '09:00', message: 'Double-booked: ACL Reconstruction & Cardiac Cath requested same slot' },
  ],
  agentUsage: [{ agent: 'Patient', calls: 120 }, { agent: 'Surgery', calls: 34 }, { agent: 'Engagement', calls: 89 }],
  reminderStats: { sent: 56, acknowledged: 48, overdue: 8 },
};

export default function AdminAnalytics() {
  const [data, setData] = useState(isMockMode() ? mockAnalytics : null);
  const [loading, setLoading] = useState(!isMockMode());
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getAnalytics()
      .then((d) => {
        if (cancelled) return;
        setData(d || {});
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load analytics');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading && !isMockMode()) {
    return <div className="admin-page page-enter"><p>Loading analytics…</p></div>;
  }
  if (error) {
    return <div className="admin-page page-enter"><p className="admin-error">{error}</p><button className="btn btn--primary" onClick={() => window.location.reload()}>Retry</button></div>;
  }

  const ot = data?.otUtilization || [];
  const conflicts = data?.otConflicts || [];
  const otRecommendations = data?.otRecommendations || data?.otRecommendation || '';
  const agents = data?.agentUsage || [];
  const reminders = data?.reminderStats || {};

  return (
    <div className="admin-page page-enter">
      <h1 className="admin-page__title">📊 Analytics</h1>
      <p className="admin-page__desc">OT utilization, agent usage, and reminder stats (from RDS).</p>
      <div className="admin-cards">
        <div className="admin-card">
          <h2 className="admin-card__title">OT Utilization</h2>
          <ul className="admin-list">
            {ot.map((row) => (
              <li key={row.ot} className="admin-list__row">
                <span>{row.ot}</span>
                <span>{row.percent != null ? `${row.percent}%` : '—'}</span>
              </li>
            ))}
          </ul>
          {otRecommendations && (
            <p className="admin-muted" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)' }}>Recommendations: {otRecommendations}</p>
          )}
        </div>
        <div className="admin-card">
          <h2 className="admin-card__title">OT Conflicts</h2>
          <ul className="admin-list">
            {conflicts.length === 0 ? <li className="admin-list__row"><span className="admin-muted">No conflicts</span></li> : conflicts.map((c) => (
              <li key={c.id || c.ot + c.date + c.time} className="admin-list__row admin-list__row--conflict">
                <span>{c.ot} {c.date} {c.time}</span>
                <span className="admin-muted">{c.message}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="admin-card">
          <h2 className="admin-card__title">Agent Usage (calls)</h2>
          <ul className="admin-list">
            {agents.map((row) => (
              <li key={row.agent} className="admin-list__row">
                <span>{row.agent}</span>
                <span>{row.calls ?? '—'}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="admin-card">
          <h2 className="admin-card__title">Reminder Stats</h2>
          <ul className="admin-list">
            <li className="admin-list__row"><span>Sent</span><span>{reminders.sent ?? '—'}</span></li>
            <li className="admin-list__row"><span>Acknowledged</span><span>{reminders.acknowledged ?? '—'}</span></li>
            <li className="admin-list__row"><span>Overdue</span><span>{reminders.overdue ?? '—'}</span></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
