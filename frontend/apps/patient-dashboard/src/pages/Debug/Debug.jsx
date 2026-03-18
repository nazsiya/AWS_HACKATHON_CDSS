/**
 * Dev-only debug/status page: API health, auth status, last sync timestamps, error surface.
 * Shown only when import.meta.env.DEV is true.
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { config, isCognitoEnabled, isMockMode } from '../../api/config';
import './Debug.css';

export default function Debug() {
  const { user, loading } = useAuth();
  const [health, setHealth] = useState({ status: 'idle', ok: null, latency: null, error: null });
  const [lastSync, setLastSync] = useState(null);
  const [errors, setErrors] = useState([]);

  const checkHealth = useCallback(async () => {
    const base = config.apiUrl?.replace(/\/$/, '') || '';
    if (!base) {
      setHealth({ status: 'done', ok: false, error: 'No API URL' });
      return;
    }
    setHealth((prev) => ({ ...prev, status: 'loading' }));
    const t0 = performance.now();
    try {
      const token = user?.token ?? user?.id;
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch(`${base}/health`, { method: 'GET', headers });
      const latency = Math.round(performance.now() - t0);
      const body = await r.json().catch(() => ({}));
      setHealth({ status: 'done', ok: r.ok, latency, body, error: null });
      setLastSync(new Date().toISOString());
    } catch (e) {
      setHealth({ status: 'done', ok: false, error: e.message });
      setErrors((prev) => [{ time: new Date().toISOString(), message: e.message }, ...prev.slice(0, 9)]);
    }
  }, [user?.token, user?.id]);

  useEffect(() => {
    if (!config.apiUrl) return;
    checkHealth();
  }, [checkHealth]);

  const runSmokeCheck = async () => {
    const base = config.apiUrl?.replace(/\/$/, '') || '';
    if (!base) {
      setErrors((prev) => [{ time: new Date().toISOString(), message: 'No API URL' }, ...prev.slice(0, 9)]);
      return;
    }
    const token = user?.token ?? user?.id;
    try {
      const r = await fetch(`${base}/health`, { method: 'GET', headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setLastSync(new Date().toISOString());
    } catch (e) {
      setErrors((prev) => [{ time: new Date().toISOString(), message: e.message }, ...prev.slice(0, 9)]);
    }
  };

  if (!import.meta.env.DEV) {
    return (
      <div className="page-card debug-page">
        <p>Debug panel is only available in development.</p>
      </div>
    );
  }

  return (
    <div className="page-card debug-page">
      <h1 className="page-title">Connection status (dev only)</h1>
      <p className="debug-muted">
        API: {config.apiUrl || '—'} | Cognito: {isCognitoEnabled() ? 'on' : 'off'} | Mock: {isMockMode() ? 'on' : 'off'}
      </p>

      <section className="debug-section">
        <h3>Auth status</h3>
        {loading && <p className="debug-muted">Loading…</p>}
        {!loading && !user && <p className="debug-fail">Not signed in.</p>}
        {!loading && user && (
          <div className="debug-card">
            <strong>Signed in</strong>
            <pre className="debug-pre">
              {JSON.stringify(
                { id: user.id, name: user.name, role: user.role, hasToken: !!(user.token || user.id) },
                null,
                2
              )}
            </pre>
          </div>
        )}
      </section>

      <section className="debug-section">
        <h3>API health</h3>
        <button type="button" className="debug-btn" onClick={checkHealth} disabled={health.status === 'loading'}>
          {health.status === 'loading' ? 'Checking…' : 'Check health'}
        </button>
        {health.status === 'done' && (
          <div className="debug-card">
            {health.ok ? (
              <span className="debug-ok">OK {health.latency != null ? `${health.latency}ms` : ''}</span>
            ) : (
              <span className="debug-fail">{health.error || `HTTP error`}</span>
            )}
          </div>
        )}
      </section>

      <section className="debug-section">
        <h3>Last sync</h3>
        <p className="debug-muted">
          {lastSync ? `Last successful API check: ${lastSync}` : 'No successful check yet.'}
        </p>
        <button type="button" className="debug-btn" onClick={runSmokeCheck}>
          Run smoke check
        </button>
      </section>

      <section className="debug-section">
        <h3>Recent errors</h3>
        {errors.length === 0 && <p className="debug-muted">No recent errors.</p>}
        {errors.length > 0 && (
          <ul className="debug-list">
            {errors.map((e, i) => (
              <li key={i} className="debug-fail">
                <span className="debug-muted">{e.time}</span> {e.message}
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="debug-btn"
          onClick={() => setErrors([])}
          disabled={errors.length === 0}
        >
          Clear
        </button>
      </section>
    </div>
  );
}
