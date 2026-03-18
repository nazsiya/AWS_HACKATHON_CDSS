function MyAppointments() {
  const appointments = [
    { id: 1, date: '2025-03-05', time: '10:00 AM', doctor: 'Dr. Priya Sharma', type: 'Follow-up' },
    { id: 2, date: '2025-03-12', time: '2:30 PM', doctor: 'Dr. Vikram Patel', type: 'Consultation' },
  ];
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">My Appointments</h1>
      <p className="text-muted">View and manage your upcoming visits.</p>
      <ul style={{ marginTop: 'var(--space-6)', listStyle: 'none' }}>
        {appointments.map((a) => (
          <li key={a.id} style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-3)' }}>
            <strong>{a.date} at {a.time}</strong> — {a.doctor} ({a.type})
          </li>
        ))}
      </ul>
    </div>
  );
}

export default MyAppointments;
