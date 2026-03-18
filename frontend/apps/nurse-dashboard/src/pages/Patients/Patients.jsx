function Patients() {
  const list = [
    { id: 1, name: 'Rahul Kumar', ward: 'General', status: 'Waiting', hr: 72, bp: '120/80', spo2: 98 },
    { id: 2, name: 'Meera Singh', ward: 'OPD', status: 'In consultation', hr: 88, bp: '130/85', spo2: 96 },
  ];
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Patients</h1>
      <p className="text-muted">Patient list and vitals.</p>
      <ul style={{ marginTop: 'var(--space-6)', listStyle: 'none' }}>
        {list.map((p) => (
          <li key={p.id} style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-3)' }}>
            <strong>{p.name}</strong> — {p.ward} · {p.status}<br />
            <small>HR {p.hr} · BP {p.bp} · SpO₂ {p.spo2}%</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Patients;
