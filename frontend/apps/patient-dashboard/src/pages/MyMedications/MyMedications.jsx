function MyMedications() {
  const meds = [
    { name: 'Paracetamol', dosage: '500mg', frequency: 'Twice daily', until: '2025-03-15' },
    { name: 'Amoxicillin', dosage: '250mg', frequency: 'Three times daily', until: '2025-03-10' },
    { name: 'Vitamin D', dosage: '1000 IU', frequency: 'Once daily', until: 'Ongoing' },
  ];
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">My Medications</h1>
      <p className="text-muted">Your current prescriptions.</p>
      <ul style={{ marginTop: 'var(--space-6)', listStyle: 'none' }}>
        {meds.map((m, i) => (
          <li key={i} style={{ padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-3)' }}>
            <strong>{m.name}</strong> — {m.dosage}, {m.frequency}. Until: {m.until}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default MyMedications;
