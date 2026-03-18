import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getResources } from '../../api/client';
import '../Settings/AdminShared.css';

const mockResources = {
  ots: [
    { id: 'OT-1', name: 'OT Room 1 (Main)', status: 'in-use', nextFree: '2026-03-05 14:00', lastUpdated: '2026-03-02T10:15:00Z' },
    { id: 'OT-2', name: 'OT Room 2 (Minor)', status: 'available', nextFree: null, lastUpdated: '2026-03-02T10:10:00Z' },
    { id: 'OT-3', name: 'Cardiac OT', status: 'maintenance', nextFree: '2026-03-06 08:00', lastUpdated: '2026-03-02T09:00:00Z' },
  ],
  equipment: [
    { id: 'EQ-1', name: 'C-Arm Fluoroscopy', status: 'in-use', location: 'OT-1', lastUpdated: '2026-03-02T10:00:00Z' },
    { id: 'EQ-2', name: 'Surgical Robot (Da Vinci)', status: 'available', location: 'OT-2', lastUpdated: '2026-03-02T09:45:00Z' },
    { id: 'EQ-3', name: 'Laser Lithotripsy', status: 'available', location: '—', lastUpdated: '2026-03-02T08:30:00Z' },
  ],
  specialists: [
    { id: 'DR-1', name: 'Dr. Vikram Patel', specialty: 'Orthopedics', status: 'available', lastUpdated: '2026-03-02T10:00:00Z' },
    { id: 'DR-2', name: 'Dr. Meena Rao', specialty: 'Cardiology', status: 'busy', lastUpdated: '2026-03-02T09:55:00Z' },
    { id: 'DR-3', name: 'Dr. Priya Sharma', specialty: 'General', status: 'available', lastUpdated: '2026-03-02T10:05:00Z' },
    { id: 'DR-4', name: 'Dr. Suresh Reddy', specialty: 'General Surgery', status: 'on-call', lastUpdated: '2026-03-02T08:00:00Z' },
  ],
};

export default function AdminResources() {
  const [data, setData] = useState(isMockMode() ? mockResources : { ots: [], equipment: [], specialists: [] });
  const [loading, setLoading] = useState(!isMockMode());
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getResources()
      .then((d) => {
        if (cancelled) return;
        setData({
          ots: d?.ots ?? d?.operation_theaters ?? [],
          equipment: d?.equipment ?? d?.equipments ?? [],
          specialists: d?.specialists ?? d?.doctors ?? [],
        });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load resources');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading && !isMockMode()) {
    return <div className="admin-page page-enter"><p>Loading resources…</p></div>;
  }
  if (error) {
    return <div className="admin-page page-enter"><p className="admin-error">{error}</p><button className="btn btn--primary" onClick={() => window.location.reload()}>Retry</button></div>;
  }

  const ots = data?.ots || [];
  const equipment = data?.equipment || [];
  const specialists = data?.specialists || [];

  const formatTimestamp = (ts) => {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch { return ts; }
  };

  return (
    <div className="admin-page page-enter">
      <h1 className="admin-page__title">🛠️ Resources</h1>
      <p className="admin-page__desc">Real-time OT and equipment availability (status with timestamps). Resolve conflicts from Analytics.</p>
      <div className="admin-cards">
        <div className="admin-card">
          <h2 className="admin-card__title">Operation Theaters</h2>
          <ul className="admin-list">
            {ots.map((r) => (
              <li key={r.id} className="admin-list__row">
                <span>{r.name || r.id}</span>
                <span className={`admin-badge admin-badge--${(r.status || 'available').replace('-', '')}`}>{r.status || 'available'}</span>
                {r.nextFree && <span className="admin-muted" style={{ fontSize: 'var(--text-xs)' }}>Free: {r.nextFree}</span>}
                {r.lastUpdated && <span className="admin-muted" style={{ fontSize: 'var(--text-xs)', display: 'block' }}>Updated: {formatTimestamp(r.lastUpdated)}</span>}
              </li>
            ))}
          </ul>
        </div>
        <div className="admin-card">
          <h2 className="admin-card__title">Equipment</h2>
          <ul className="admin-list">
            {equipment.map((r) => (
              <li key={r.id} className="admin-list__row">
                <span>{r.name || r.id}</span>
                <span className={`admin-badge admin-badge--${(r.status || 'available').replace('-', '')}`}>{r.status || 'available'}</span>
                {r.location && <span className="admin-muted">@{r.location}</span>}
                {r.lastUpdated && <span className="admin-muted" style={{ fontSize: 'var(--text-xs)', display: 'block' }}>Updated: {formatTimestamp(r.lastUpdated)}</span>}
              </li>
            ))}
          </ul>
        </div>
        <div className="admin-card">
          <h2 className="admin-card__title">Available doctors & specialists</h2>
          <ul className="admin-list">
            {specialists.map((r) => (
              <li key={r.id} className="admin-list__row">
                <span>{r.name || r.id}</span>
                <span className="admin-muted">{r.specialty || '—'}</span>
                <span className={`admin-badge admin-badge--${(r.status || 'available').replace('-', '')}`}>{r.status || 'available'}</span>
                {r.lastUpdated && <span className="admin-muted" style={{ fontSize: 'var(--text-xs)' }}>{formatTimestamp(r.lastUpdated)}</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
