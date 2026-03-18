/**
 * Dev-only debug panel: endpoint health, token/claims viewer, RBAC quick tests, WebSocket monitor.
 * Shown only when import.meta.env.DEV is true. Do not expose in production builds.
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { config, isCognitoEnabled } from '../../api/config';
import { connectWs, disconnectWs, addWsListener, isWsEnabled } from '../../api/websocket';
import './Debug.css';

function decodeJwtPayload(token) {
  if (!token || typeof token !== 'string') return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
}

function EndpointHealth({ baseUrl, token }) {
  const [results, setResults] = useState({ health: null, dashboard: null });

  const check = useCallback(async () => {
    const base = baseUrl?.replace(/\/$/, '') || '';
    if (!base) {
      setResults({ health: { ok: false, error: 'No API URL' }, dashboard: null });
      return;
    }
    setResults({ health: null, dashboard: null });

    const t0 = performance.now();
    try {
      const r = await fetch(`${base}/health`, { method: 'GET' });
      const body = await r.json().catch(() => ({}));
      const latency = Math.round(performance.now() - t0);
      setResults((prev) => ({
        ...prev,
        health: { ok: r.ok, status: r.status, latency, body },
      }));
    } catch (e) {
      setResults((prev) => ({
        ...prev,
        health: { ok: false, error: e.message },
      }));
    }

    if (token) {
      const t1 = performance.now();
      try {
        const r = await fetch(`${base}/dashboard`, {
          method: 'GET',
          headers: { Authorization: `Bearer ${token}` },
        });
        const latency = Math.round(performance.now() - t1);
        setResults((prev) => ({
          ...prev,
          dashboard: { ok: r.ok, status: r.status, latency },
        }));
      } catch (e) {
        setResults((prev) => ({
          ...prev,
          dashboard: { ok: false, error: e.message },
        }));
      }
    }
  }, [baseUrl, token]);

  useEffect(() => {
    check();
  }, [check]);

  return (
    <section className="debug-section">
      <h3>Endpoint health</h3>
      <p className="debug-muted">Base: {config.apiUrl || '(not set)'}</p>
      <button type="button" className="debug-btn" onClick={check}>
        Refresh
      </button>
      <div className="debug-grid">
        <div className="debug-card">
          <strong>GET /health</strong>
          {results.health == null && <span>Checking…</span>}
          {results.health?.ok && (
            <span className="debug-ok">OK {results.health.latency}ms</span>
          )}
          {results.health && !results.health.ok && (
            <span className="debug-fail">
              {results.health.status || results.health.error}
            </span>
          )}
        </div>
        <div className="debug-card">
          <strong>GET /dashboard (auth)</strong>
          {!token && <span className="debug-muted">No token</span>}
          {token && results.dashboard == null && <span>Checking…</span>}
          {token && results.dashboard?.ok && (
            <span className="debug-ok">OK {results.dashboard.latency}ms</span>
          )}
          {token && results.dashboard && !results.dashboard.ok && (
            <span className="debug-fail">
              {results.dashboard.status || results.dashboard.error}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

function TokenClaims({ user }) {
  const payload = user?.token ? decodeJwtPayload(user.token) : null;
  return (
    <section className="debug-section">
      <h3>Token &amp; claims</h3>
      {!user && <p className="debug-muted">Not signed in.</p>}
      {user && (
        <>
          <div className="debug-card">
            <strong>User</strong>
            <pre className="debug-pre">
              {JSON.stringify(
                { id: user.id, name: user.name, email: user.email, role: user.role },
                null,
                2
              )}
            </pre>
          </div>
          {payload && (
            <div className="debug-card">
              <strong>JWT payload (no secrets)</strong>
              <pre className="debug-pre">
                {JSON.stringify(
                  {
                    sub: payload.sub,
                    'custom:role': payload['custom:role'] ?? payload.role,
                    exp: payload.exp ? new Date(payload.exp * 1000).toISOString() : payload.exp,
                    iat: payload.iat,
                  },
                  null,
                  2
                )}
              </pre>
            </div>
          )}
          {user.token && !payload && (
            <p className="debug-muted">Token present but not a JWT (e.g. mock token).</p>
          )}
        </>
      )}
    </section>
  );
}

function RbacTests({ baseUrl, token }) {
  const [tests, setTests] = useState([]);
  const [running, setRunning] = useState(false);

  const run = useCallback(async () => {
    const base = baseUrl?.replace(/\/$/, '') || '';
    if (!base || !token) {
      setTests([{ name: '—', result: 'Skip', status: null, error: 'Need API URL and token' }]);
      return;
    }
    setRunning(true);
    const endpoints = [
      { name: 'GET /dashboard', path: '/dashboard' },
      { name: 'GET /api/v1/patients', path: '/api/v1/patients' },
      { name: 'GET /api/v1/schedule', path: '/api/v1/schedule' },
      { name: 'GET /api/v1/admin/audit', path: '/api/v1/admin/audit' },
    ];
    const out = [];
    for (const { name, path } of endpoints) {
      try {
        const r = await fetch(`${base}${path}`, {
          method: 'GET',
          headers: { Authorization: `Bearer ${token}` },
        });
        out.push({
          name,
          result: r.ok ? '200' : `${r.status}`,
          status: r.status,
          error: r.ok ? null : await r.text().then((t) => t.slice(0, 80)),
        });
      } catch (e) {
        out.push({ name, result: 'Err', status: null, error: e.message });
      }
    }
    setTests(out);
    setRunning(false);
  }, [baseUrl, token]);

  return (
    <section className="debug-section">
      <h3>RBAC quick tests</h3>
      <p className="debug-muted">Calls with current token; expect 200 or 403 by role.</p>
      <button
        type="button"
        className="debug-btn"
        onClick={run}
        disabled={running || !token || !config.apiUrl}
      >
        {running ? 'Running…' : 'Run tests'}
      </button>
      {tests.length > 0 && (
        <ul className="debug-list">
          {tests.map((t, i) => (
            <li key={i} className={t.status === 200 ? 'debug-ok' : t.status === 403 ? 'debug-forbidden' : 'debug-fail'}>
              {t.name} → {t.result}
              {t.error && <span className="debug-muted"> {t.error}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function WsMonitor({ user }) {
  const [status, setStatus] = useState('disconnected');
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    if (!isWsEnabled()) return;
    const unsub = addWsListener((data) => {
      setMessages((prev) => [JSON.stringify(data).slice(0, 200), ...prev.slice(0, 19)]);
    });
    return unsub;
  }, []);

  const handleConnect = () => {
    connectWs({
      doctorId: user?.id || '',
      onOpen: () => setStatus('connected'),
      onClose: () => setStatus('disconnected'),
      onError: () => setStatus('error'),
    });
  };

  const handleDisconnect = () => {
    disconnectWs();
    setStatus('disconnected');
  };

  return (
    <section className="debug-section">
      <h3>WebSocket monitor</h3>
      <p className="debug-muted">URL: {config.wsUrl || '(not set)'}</p>
      {!isWsEnabled() && <p className="debug-muted">WebSocket not configured (VITE_WS_URL).</p>}
      {isWsEnabled() && (
        <>
          <div className="debug-inline">
            <button type="button" className="debug-btn" onClick={handleConnect} disabled={status === 'connected'}>
              Connect
            </button>
            <button type="button" className="debug-btn" onClick={handleDisconnect} disabled={status !== 'connected'}>
              Disconnect
            </button>
            <span className={`debug-status debug-status-${status}`}>{status}</span>
          </div>
          <div className="debug-card">
            <strong>Last 20 messages</strong>
            <ul className="debug-list debug-messages">
              {messages.length === 0 && <li className="debug-muted">No messages yet.</li>}
              {messages.map((m, i) => (
                <li key={i} className="debug-monospace">{m}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}

export default function Debug() {
  const { user } = useAuth();
  const token = user?.token ?? user?.id ?? null;

  if (!import.meta.env.DEV) {
    return (
      <div className="page-card debug-page">
        <p>Debug panel is only available in development.</p>
      </div>
    );
  }

  return (
    <div className="page-card debug-page">
      <h1 className="page-title">Debug panel (dev only)</h1>
      <p className="debug-muted">
        REST base: {config.apiUrl || '—'} | Cognito: {isCognitoEnabled() ? 'on' : 'off'}
      </p>
      <EndpointHealth baseUrl={config.apiUrl} token={token} />
      <TokenClaims user={user} />
      <RbacTests baseUrl={config.apiUrl} token={token} />
      <WsMonitor user={user} />
    </div>
  );
}
