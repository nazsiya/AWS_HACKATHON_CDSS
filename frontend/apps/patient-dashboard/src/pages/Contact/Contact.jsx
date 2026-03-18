function Contact() {
  return (
    <div className="page-card" style={{ padding: 'var(--space-6)' }}>
      <h1 className="page-title">Contact & Messages</h1>
      <p className="text-muted">Message your care team or request a callback.</p>
      <div style={{ marginTop: 'var(--space-6)', maxWidth: 400 }}>
        <p style={{ marginBottom: 'var(--space-4)' }}>For non-urgent queries, you can leave a message. For emergencies, please call the hospital or visit the ER.</p>
        <textarea placeholder="Type your message..." rows={4} style={{ width: '100%', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--surface-border)', background: 'var(--surface-card)', color: 'var(--text-primary)' }} />
        <button type="button" style={{ marginTop: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', background: 'var(--color-primary)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 600, cursor: 'pointer' }}>Send message</button>
      </div>
    </div>
  );
}

export default Contact;
