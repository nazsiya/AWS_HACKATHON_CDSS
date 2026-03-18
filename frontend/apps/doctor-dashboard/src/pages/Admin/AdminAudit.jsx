import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getAuditLog } from '../../api/client';
import '../Settings/AdminShared.css';

const mockAudit = [
  { id: 1, user_id: 'u1', user_email: 'priya@cdss.ai', action: 'VIEW_PATIENT', resource: 'PT-1001', timestamp: '2026-03-01T10:15:00Z' },
  { id: 2, user_id: 'u2', user_email: 'vikram@cdss.ai', action: 'UPDATE_SURGERY', resource: 'SRG-001', timestamp: '2026-03-01T09:45:00Z' },
  { id: 3, user_id: 'u4', user_email: 'admin@cdss.ai', action: 'LOGIN', resource: '—', timestamp: '2026-03-01T08:00:00Z' },
];

export default function AdminAudit() {
  const [list, setList] = useState(isMockMode() ? mockAudit : []);
  const [loading, setLoading] = useState(!isMockMode());
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getAuditLog({ limit: 100 })
      .then((data) => {
        if (cancelled) return;
        setList(Array.isArray(data) ? data : (data.items || data.log || []));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load audit log');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const filtered = search.trim()
    ? list.filter((r) =>
        (r.user_email || '').toLowerCase().includes(search.toLowerCase()) ||
        (r.action || '').toLowerCase().includes(search.toLowerCase()) ||
        (r.resource || '').toLowerCase().includes(search.toLowerCase())
      )
    : list;

  const handleExport = () => {
    const csv = ['user_email,action,resource,timestamp', ...filtered.map((r) => `${r.user_email || ''},${r.action || ''},${r.resource || ''},${r.timestamp || ''}`)].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `cdss-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (loading && !isMockMode()) {
    return <div className="admin-page page-enter"><p>Loading audit log…</p></div>;
  }
  if (error) {
    return <div className="admin-page page-enter"><p className="admin-error">{error}</p><button className="btn btn--primary" onClick={() => window.location.reload()}>Retry</button></div>;
  }

  return (
    <div className="admin-page page-enter">
      <h1 className="admin-page__title">📋 Audit Log</h1>
      <p className="admin-page__desc">DISHA-aligned access and action log. Search and export for compliance.</p>
      <div className="admin-toolbar">
        <input
          type="text"
          className="admin-search"
          placeholder="Search by user, action, resource…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" className="btn btn--primary" onClick={handleExport}>Export CSV</button>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id || r.timestamp}>
                <td>{r.user_email || r.user_id}</td>
                <td><code>{r.action}</code></td>
                <td>{r.resource}</td>
                <td>{r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
