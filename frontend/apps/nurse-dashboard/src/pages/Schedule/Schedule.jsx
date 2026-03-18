function Schedule() {
  const slots = [
    { time: '09:00', patient: 'Rahul Kumar', type: 'Follow-up' },
    { time: '09:30', patient: 'Meera Singh', type: 'Consultation' },
    { time: '10:00', patient: '—', type: 'Free' },
  ];
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Schedule</h1>
      <p className="text-muted">Today&apos;s appointments and rounds.</p>
      <ul style={{ marginTop: 'var(--space-6)', listStyle: 'none' }}>
        {slots.map((s, i) => (
          <li key={i} style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--surface-border)', display: 'flex', justifyContent: 'space-between' }}>
            <span>{s.time}</span>
            <span>{s.patient}</span>
            <span style={{ color: 'var(--text-muted)' }}>{s.type}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Schedule;
