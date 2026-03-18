function MyRecords() {
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">My Health Records</h1>
      <p className="text-muted">Lab results, visit summaries, and documents.</p>
      <p style={{ marginTop: 'var(--space-4)', color: 'var(--text-muted)' }}>No records to display. After your visits, summaries will appear here.</p>
    </div>
  );
}

export default MyRecords;
