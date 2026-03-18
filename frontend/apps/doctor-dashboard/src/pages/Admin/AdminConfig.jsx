import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { getSystemConfig, updateSystemConfig } from '../../api/client';
import '../Settings/AdminShared.css';

const mockConfig = {
  mcpHospitalEndpoint: 'https://hospital-api.example.com',
  mcpAbdmEndpoint: 'https://abdm.example.com',
  featureFlags: { aiAssist: true, voiceInput: false },
};

export default function AdminConfig() {
  const [config, setConfig] = useState(isMockMode() ? mockConfig : {});
  const [loading, setLoading] = useState(!isMockMode());
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (isMockMode()) return;
    let cancelled = false;
    setLoading(true);
    getSystemConfig()
      .then((data) => {
        if (cancelled) return;
        setConfig(data || {});
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load config');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const handleSave = () => {
    if (isMockMode()) {
      setMessage('Saved (mock).');
      return;
    }
    setSaving(true);
    setMessage('');
    updateSystemConfig(config)
      .then(() => setMessage('Saved.'))
      .catch((err) => setMessage(err.message || 'Save failed'))
      .finally(() => setSaving(false));
  };

  const update = (key, value) => setConfig((prev) => ({ ...prev, [key]: value }));

  if (loading && !isMockMode()) {
    return <div className="admin-page page-enter"><p>Loading config…</p></div>;
  }
  if (error && !isMockMode()) {
    return <div className="admin-page page-enter"><p className="admin-error">{error}</p><button className="btn btn--primary" onClick={() => window.location.reload()}>Retry</button></div>;
  }

  return (
    <div className="admin-page page-enter">
      <h1 className="admin-page__title">⚙️ System Config</h1>
      <p className="admin-page__desc">MCP endpoints and feature flags (stored in RDS or Parameter Store).</p>
      <div className="admin-section">
        <label className="admin-label">MCP Hospital endpoint</label>
        <input
          type="url"
          className="admin-input"
          value={config.mcpHospitalEndpoint || ''}
          onChange={(e) => update('mcpHospitalEndpoint', e.target.value)}
          placeholder="https://..."
        />
      </div>
      <div className="admin-section">
        <label className="admin-label">MCP ABDM endpoint</label>
        <input
          type="url"
          className="admin-input"
          value={config.mcpAbdmEndpoint || ''}
          onChange={(e) => update('mcpAbdmEndpoint', e.target.value)}
          placeholder="https://..."
        />
      </div>
      <div className="admin-section">
        <label className="admin-label">Feature: AI Assist</label>
        <input
          type="checkbox"
          checked={!!(config.featureFlags && config.featureFlags.aiAssist)}
          onChange={(e) => update('featureFlags', { ...(config.featureFlags || {}), aiAssist: e.target.checked })}
        />
      </div>
      <div className="admin-section">
        <label className="admin-label">Feature: Voice input</label>
        <input
          type="checkbox"
          checked={!!(config.featureFlags && config.featureFlags.voiceInput)}
          onChange={(e) => update('featureFlags', { ...(config.featureFlags || {}), voiceInput: e.target.checked })}
        />
      </div>
      <div className="admin-toolbar">
        <button type="button" className="btn btn--primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        {message && <span className="admin-message">{message}</span>}
      </div>
    </div>
  );
}
