import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getUsers } from '../../api/client';
import '../Settings/AdminShared.css';

const mockUsers = [
  { id: 'u1', name: 'Dr. Priya Sharma', email: 'priya@cdss.ai', role: 'doctor', status: 'active' },
  { id: 'u2', name: 'Dr. Vikram Patel', email: 'vikram@cdss.ai', role: 'surgeon', status: 'active' },
  { id: 'u3', name: 'Nurse Anjali', email: 'anjali@cdss.ai', role: 'nurse', status: 'active' },
  { id: 'u4', name: 'Admin Sameer', email: 'admin@cdss.ai', role: 'admin', status: 'active' },
];

export default function AdminUsers() {
  const [list, setList] = useState(isMockMode() ? mockUsers : []);
  const [loading, setLoading] = useState(!isMockMode());
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getUsers()
      .then((data) => {
        if (cancelled) return;
        setList(Array.isArray(data) ? data : (data.users || data.items || []));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load users');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading && !isMockMode()) {
    return <div className="admin-page page-enter"><p>Loading users…</p></div>;
  }
  if (error) {
    return <div className="admin-page page-enter"><p className="admin-error">{error}</p><button className="btn btn--primary" onClick={() => window.location.reload()}>Retry</button></div>;
  }

  return (
    <div className="admin-page page-enter">
      <h1 className="admin-page__title">👥 Users & Roles</h1>
      <p className="admin-page__desc">Manage staff accounts and role assignments (Cognito + RDS).</p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {list.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td><span className="admin-badge admin-badge--role">{u.role}</span></td>
                <td><span className="admin-badge admin-badge--active">{u.status || 'active'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
