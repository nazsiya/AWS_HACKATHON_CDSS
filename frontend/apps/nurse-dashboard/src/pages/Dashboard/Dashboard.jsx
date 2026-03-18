function NurseDashboard() {
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Nurse Station — Overview</h1>
      <p className="text-muted">Patient queue and today&apos;s tasks.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-4)', marginTop: 'var(--space-6)' }}>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>👥</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>8</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Patients in queue</div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>💊</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>12</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Medications due</div>
        </div>
        <div className="stat-card" style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--surface-border)' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 'var(--space-2)' }}>🚨</div>
          <div style={{ fontWeight: 700, fontSize: 'var(--text-xl)' }}>2</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Alerts</div>
        </div>
      </div>
    </div>
  );
}

export default NurseDashboard;
