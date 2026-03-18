function Vitals() {
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Vitals</h1>
      <p className="text-muted">Record and view patient vitals.</p>
      <p style={{ marginTop: 'var(--space-4)', color: 'var(--text-muted)' }}>Enter patient ID and vitals to log. Integrates with backend when API is configured.</p>
    </div>
  );
}

export default Vitals;
