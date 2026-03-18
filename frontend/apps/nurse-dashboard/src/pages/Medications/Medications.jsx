function Medications() {
  const due = [
    { patient: 'Rahul Kumar', medication: 'Paracetamol 500mg', time: '10:00 AM', done: false },
    { patient: 'Meera Singh', medication: 'Amoxicillin 250mg', time: '10:30 AM', done: false },
  ];
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Medication Administration</h1>
      <p className="text-muted">Medications due and sign-off.</p>
      <ul style={{ marginTop: 'var(--space-6)', listStyle: 'none' }}>
        {due.map((m, i) => (
          <li key={i} style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-3)' }}>
            <strong>{m.patient}</strong> — {m.medication} at {m.time}
            <button style={{ marginLeft: 'var(--space-3)', padding: 'var(--space-1) var(--space-2)', fontSize: 'var(--text-xs)', background: 'var(--color-primary)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>Mark done</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Medications;
