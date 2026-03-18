/**
 * Shows a banner when the backend reports database unavailable (e.g. no SSH tunnel or DATABASE_URL).
 * Only active when using live API (VITE_USE_MOCK=false). Check GET /health before relying on data.
 */
import { useState, useEffect } from 'react';
import { config, isMockMode } from '../../api/config';

export default function ApiHealthBanner() {
  const [dbStatus, setDbStatus] = useState(null); // 'connected' | 'unavailable' | null (loading/not checked)
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (isMockMode() || !config.apiUrl) {
      setDbStatus(null);
      return;
    }
    let cancelled = false;
    fetch(`${config.apiUrl}/health`, { method: 'GET' })
      .then((r) => (r.ok ? r.json() : {}))
      .then((body) => {
        if (cancelled) return;
        // Align with backend: health returns { database: "connected" | "unavailable" }
        if (body && body.database === 'connected') setDbStatus('connected');
        else setDbStatus('unavailable');
      })
      .catch(() => {
        if (!cancelled) setDbStatus('unavailable');
      });
    return () => { cancelled = true; };
  }, []);

  if (dbStatus !== 'unavailable' || dismissed) return null;

  return (
    <div className="api-health-banner" role="alert">
      <span className="api-health-banner__text">
        Backend is not connected to the database. You may see mock or empty data.
        For real data: (Local) start the DB tunnel (e.g. <code>scripts/start_ssh_tunnel.ps1</code>), set{' '}
        <code>DATABASE_URL</code> in backend <code>.env</code>, then restart the API.
        (Deployed) Run migrations and RDS IAM grant once—see <code>scripts/run_after_tunnel.ps1</code> and docs.
      </span>
      <button
        type="button"
        className="api-health-banner__dismiss"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss banner"
      >
        ×
      </button>
      <style>{`
        .api-health-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem 1rem;
          background: #fef3c7;
          border-bottom: 1px solid #f59e0b;
          color: #92400e;
          font-size: 0.875rem;
        }
        .api-health-banner__text { flex: 1; }
        .api-health-banner__text code { font-size: 0.8em; background: rgba(0,0,0,0.06); padding: 0.1em 0.3em; }
        .api-health-banner__dismiss {
          background: none;
          border: none;
          font-size: 1.25rem;
          cursor: pointer;
          color: inherit;
          line-height: 1;
        }
      `}</style>
    </div>
  );
}
