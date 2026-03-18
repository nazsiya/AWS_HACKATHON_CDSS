import { useAuth } from '../../context/AuthContext';

export default function Profile() {
  const { user } = useAuth();
  if (!user) return null;
  const initials = user.name.split(' ').map((n) => n[0]).join('');

  return (
    <div className="profile-page page-enter" style={{ padding: '24px' }}>
      <h1 className="profile-page__title">Profile</h1>
      <div className="profile-page__card" style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '24px', marginTop: '16px', maxWidth: '400px' }}>
        <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: '#2563eb', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', fontWeight: 700 }}>
          {initials}
        </div>
        <p style={{ margin: '16px 0 4px', fontWeight: 600, color: '#111827' }}>{user.name}</p>
        <p style={{ margin: 0, fontSize: '14px', color: '#6b7280' }}>{user.email}</p>
        <p style={{ margin: '8px 0 0', fontSize: '12px', color: '#9ca3af', textTransform: 'capitalize' }}>Role: {user.role}</p>
      </div>
    </div>
  );
}
