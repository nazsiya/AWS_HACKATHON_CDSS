function PatientDashboard() {
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">My Health Overview</h1>
      <p className="text-muted">Welcome to your patient dashboard.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-4)', marginTop: 'var(--space-6)' }}>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>📅</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>2</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Upcoming appointments</div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>💊</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>3</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Active medications</div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>📋</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>—</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Recent records</div>
        </div>
      </div>
    </div>
  );
}

export default PatientDashboard;
