import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './AdminDashboard.css';

/* ─── Helpers ─── */
function rand(base, variance) {
  return Math.max(0, base + Math.floor(Math.random() * variance * 2 - variance));
}

function StatusDot({ status }) {
  const map = { green: 'green', amber: 'amber', red: 'red', healthy: 'green', degraded: 'amber', down: 'red' };
  const cls = map[status] || 'green';
  return <span className={`status-dot status-dot--${cls}`} />;
}

function StatusTag({ status, label }) {
  const map = { green: 'green', amber: 'amber', red: 'red', healthy: 'green', degraded: 'amber', down: 'red',
    operational: 'green', maintenance: 'amber', offline: 'red', enabled: 'green', disabled: 'red' };
  const cls = map[status] || 'green';
  return (
    <span className={`status-tag status-tag--${cls}`}>
      <StatusDot status={status} />
      {label}
    </span>
  );
}

/* ─── Mock Data Generator ─── */
function generateMockData() {
  return {
    kpi: {
      totalDoctors: rand(24, 3),
      totalPatients: rand(312, 20),
      surgeriesScheduled: rand(8, 3),
      otUtilization: rand(72, 10),
      activeAgents: rand(5, 1),
      criticalAlerts: rand(3, 2),
    },
    resource: {
      available: rand(10, 3),
      busy: rand(8, 3),
      onCall: rand(4, 2),
      otAvailable: rand(3, 1),
      otInUse: rand(4, 2),
      otMaintenance: rand(1, 1),
      equipmentStatus: Math.random() > 0.2 ? 'operational' : 'maintenance',
      conflicts: rand(2, 2),
      replacementTriggers: rand(1, 1),
    },
    scheduling: {
      totalSurgeries: rand(8, 3),
      completed: rand(3, 2),
      inProgress: rand(2, 1),
      upcoming: rand(3, 2),
      otUtilization: rand(72, 10),
      doubleBookings: rand(1, 1),
      bufferViolations: rand(2, 2),
      replacementLog: rand(3, 2),
    },
    agents: {
      patientAgent: rand(14, 5),
      surgeryAgent: rand(6, 3),
      resourceSync: Math.random() > 0.15 ? 'healthy' : 'degraded',
      schedulingDecisions: rand(22, 8),
      remindersSent: rand(45, 15),
      failureAlerts: rand(1, 1),
      mcpHealth: Math.random() > 0.1 ? 'healthy' : 'degraded',
    },
    alerts: {
      criticalPatient: rand(3, 2),
      drugInteraction: rand(4, 3),
      escalatedNonAdherence: rand(2, 2),
      emergencyProtocol: rand(1, 1),
      unacknowledged: rand(2, 2),
    },
    audit: {
      totalLogins: rand(156, 30),
      failedLogins: rand(4, 3),
      dataAccessLogs: rand(892, 100),
      sensitiveAccess: rand(12, 5),
      lastBackup: '2026-03-05 01:30 IST',
      encryptionStatus: 'enabled',
    },
    infra: {
      rds: Math.random() > 0.05 ? 'healthy' : 'degraded',
      bedrock: Math.random() > 0.1 ? 'healthy' : 'degraded',
      mcp: Math.random() > 0.1 ? 'healthy' : 'degraded',
      apiGateway: Math.random() > 0.05 ? 'healthy' : 'degraded',
      uptime: (99 + Math.random() * 0.99).toFixed(2),
      avgResponseMs: rand(142, 40),
    },
  };
}

/* ─── Main Component ─── */
export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(generateMockData);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [hospital, setHospital] = useState('all');
  const [dateRange, setDateRange] = useState('today');

  const refresh = useCallback(() => {
    setData(generateMockData());
    setLastRefresh(new Date());
  }, []);

  useEffect(() => {
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const utilColor = data.scheduling.otUtilization > 85 ? 'red' : data.scheduling.otUtilization > 60 ? 'amber' : 'green';

  return (
    <div className="admin-dashboard">
      {/* ═══ Top Bar ═══ */}
      <header className="admin-topbar">
        <div className="admin-topbar__left">
          <div className="admin-topbar__logo">
            <div className="admin-topbar__logo-icon">C</div>
            <div className="admin-topbar__logo-text">
              <span className="admin-topbar__logo-title">CDSS Admin</span>
              <span className="admin-topbar__logo-subtitle">System Monitoring</span>
            </div>
          </div>
        </div>

        <div className="admin-topbar__controls">
          <select
            id="admin-hospital-filter"
            className="admin-topbar__select"
            value={hospital}
            onChange={(e) => setHospital(e.target.value)}
          >
            <option value="all">All Locations</option>
            <option value="main">Main Campus</option>
            <option value="north">North Wing</option>
            <option value="south">South Facility</option>
          </select>

          <select
            id="admin-date-filter"
            className="admin-topbar__select"
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
          >
            <option value="today">Today</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>

          <div className="admin-topbar__refresh-badge">
            <span className="admin-topbar__refresh-dot" />
            Live · {lastRefresh.toLocaleTimeString()}
          </div>

          <button id="admin-logout-btn" className="admin-topbar__logout-btn" onClick={handleLogout}>
            🚪 Sign Out
          </button>
        </div>
      </header>

      {/* ═══ Body ═══ */}
      <div className="admin-dashboard__body">

        {/* ─── 1. KPI Strip ─── */}
        <section className="admin-kpi-strip" id="kpi-strip">
          <div className="admin-kpi-card admin-kpi-card--primary">
            <span className="admin-kpi-card__icon">🩺</span>
            <span className="admin-kpi-card__value">{data.kpi.totalDoctors}</span>
            <span className="admin-kpi-card__label">Total Doctors (Active)</span>
          </div>
          <div className="admin-kpi-card admin-kpi-card--secondary">
            <span className="admin-kpi-card__icon">👥</span>
            <span className="admin-kpi-card__value">{data.kpi.totalPatients}</span>
            <span className="admin-kpi-card__label">Total Patients (Active)</span>
          </div>
          <div className="admin-kpi-card admin-kpi-card--accent">
            <span className="admin-kpi-card__icon">🔪</span>
            <span className="admin-kpi-card__value">{data.kpi.surgeriesScheduled}</span>
            <span className="admin-kpi-card__label">Surgeries Scheduled Today</span>
          </div>
          <div className="admin-kpi-card admin-kpi-card--warning">
            <span className="admin-kpi-card__icon">📊</span>
            <span className="admin-kpi-card__value">{data.kpi.otUtilization}%</span>
            <span className="admin-kpi-card__label">OT Utilization</span>
          </div>
          <div className="admin-kpi-card admin-kpi-card--success">
            <span className="admin-kpi-card__icon">🤖</span>
            <span className="admin-kpi-card__value">{data.kpi.activeAgents}</span>
            <span className="admin-kpi-card__label">Active AI Agents</span>
          </div>
          <div className="admin-kpi-card admin-kpi-card--critical">
            <span className="admin-kpi-card__icon">🚨</span>
            <span className="admin-kpi-card__value">{data.kpi.criticalAlerts}</span>
            <span className="admin-kpi-card__label">Critical Alerts</span>
          </div>
        </section>

        {/* ─── 2 & 3. Resource + Scheduling ─── */}
        <div className="admin-grid admin-animate-1">
          {/* Resource Agent Monitoring */}
          <section className="admin-panel" id="resource-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--resource">📡</div>
                <span className="admin-panel__title">Resource Agent Monitoring</span>
              </div>
              {data.resource.conflicts > 0 ? (
                <span className="admin-panel__badge admin-panel__badge--warning">{data.resource.conflicts} Conflicts</span>
              ) : (
                <span className="admin-panel__badge">All Clear</span>
              )}
            </div>
            <div className="admin-panel__body">
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Doctor Availability</span>
                <span className="admin-metric-row__value">
                  <StatusDot status="green" /> {data.resource.available} Available
                  &nbsp;·&nbsp;
                  <StatusDot status="amber" /> {data.resource.busy} Busy
                  &nbsp;·&nbsp;
                  <StatusDot status="red" /> {data.resource.onCall} On-call
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">OT Status</span>
                <span className="admin-metric-row__value">
                  {data.resource.otAvailable} Available · {data.resource.otInUse} In Use · {data.resource.otMaintenance} Maintenance
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Equipment Status</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.resource.equipmentStatus} label={data.resource.equipmentStatus === 'operational' ? 'Operational' : 'Maintenance'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Resource Conflicts Detected</span>
                <span className="admin-metric-row__value">{data.resource.conflicts}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Replacement Trigger Events</span>
                <span className="admin-metric-row__value">{data.resource.replacementTriggers}</span>
              </div>
            </div>
          </section>

          {/* Scheduling & OT Optimization */}
          <section className="admin-panel" id="scheduling-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--schedule">📅</div>
                <span className="admin-panel__title">Scheduling & OT Optimization</span>
              </div>
              {data.scheduling.doubleBookings > 0 ? (
                <span className="admin-panel__badge admin-panel__badge--critical">{data.scheduling.doubleBookings} Double Booking</span>
              ) : (
                <span className="admin-panel__badge">No Conflicts</span>
              )}
            </div>
            <div className="admin-panel__body">
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Today's Surgeries</span>
                <span className="admin-metric-row__value">
                  {data.scheduling.completed} Done · {data.scheduling.inProgress} In Progress · {data.scheduling.upcoming} Upcoming
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">OT Utilization</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={utilColor} /> {data.scheduling.otUtilization}%
                </span>
              </div>
              <div style={{ padding: 'var(--space-1) 0' }}>
                <div className="admin-util-bar">
                  <div
                    className={`admin-util-bar__fill admin-util-bar__fill--${utilColor}`}
                    style={{ width: `${Math.min(data.scheduling.otUtilization, 100)}%` }}
                  />
                </div>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Double Bookings Detected</span>
                <span className="admin-metric-row__value">{data.scheduling.doubleBookings}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Buffer Time Violations</span>
                <span className="admin-metric-row__value">{data.scheduling.bufferViolations}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Replacement Doctor Activity</span>
                <span className="admin-metric-row__value">{data.scheduling.replacementLog} events</span>
              </div>
            </div>
          </section>
        </div>

        {/* ─── 4 & 5. AI Agent + Alerts ─── */}
        <div className="admin-grid admin-animate-2">
          {/* AI Agent Performance */}
          <section className="admin-panel" id="agent-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--agent">🤖</div>
                <span className="admin-panel__title">AI Agent Performance</span>
              </div>
              <StatusTag status={data.agents.mcpHealth} label={`MCP ${data.agents.mcpHealth === 'healthy' ? 'Healthy' : 'Degraded'}`} />
            </div>
            <div className="admin-panel__body">
              <div className="admin-agent-grid">
                <div className="admin-agent-card">
                  <span className="admin-agent-card__name">Patient Agent</span>
                  <span className="admin-agent-card__value">{data.agents.patientAgent} <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontWeight: 400 }}>active</span></span>
                </div>
                <div className="admin-agent-card">
                  <span className="admin-agent-card__name">Surgery Agent</span>
                  <span className="admin-agent-card__value">{data.agents.surgeryAgent} <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontWeight: 400 }}>requests</span></span>
                </div>
                <div className="admin-agent-card">
                  <span className="admin-agent-card__name">Scheduling Agent</span>
                  <span className="admin-agent-card__value">{data.agents.schedulingDecisions} <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontWeight: 400 }}>decisions</span></span>
                </div>
                <div className="admin-agent-card">
                  <span className="admin-agent-card__name">Reminders Sent</span>
                  <span className="admin-agent-card__value">{data.agents.remindersSent}</span>
                </div>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Resource Agent Sync</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.agents.resourceSync} label={data.agents.resourceSync === 'healthy' ? 'Synced' : 'Degraded'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Agent Failure Alerts</span>
                <span className="admin-metric-row__value">{data.agents.failureAlerts}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Inter-Agent Comm (MCP)</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.agents.mcpHealth} label={data.agents.mcpHealth === 'healthy' ? 'Healthy' : 'Degraded'} />
                </span>
              </div>
            </div>
          </section>

          {/* Alerts & Emergency */}
          <section className="admin-panel" id="alerts-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--alerts">🚨</div>
                <span className="admin-panel__title">Notification & Emergency Alerts</span>
              </div>
              {data.alerts.unacknowledged > 0 ? (
                <span className="admin-panel__badge admin-panel__badge--critical">{data.alerts.unacknowledged} Unread</span>
              ) : (
                <span className="admin-panel__badge">All Acknowledged</span>
              )}
            </div>
            <div className="admin-panel__body">
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Critical Patient Alerts</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.alerts.criticalPatient > 2 ? 'red' : 'amber'} />
                  {data.alerts.criticalPatient}
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Drug Interaction Alerts</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.alerts.drugInteraction > 3 ? 'red' : 'amber'} />
                  {data.alerts.drugInteraction}
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Escalated Non-Adherence</span>
                <span className="admin-metric-row__value">{data.alerts.escalatedNonAdherence}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Emergency Protocol Activations</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.alerts.emergencyProtocol > 0 ? 'red' : 'green'} />
                  {data.alerts.emergencyProtocol}
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Unacknowledged Alerts</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.alerts.unacknowledged > 1 ? 'red' : data.alerts.unacknowledged > 0 ? 'amber' : 'green'} />
                  {data.alerts.unacknowledged}
                </span>
              </div>
            </div>
          </section>
        </div>

        {/* ─── 6 & 7. Audit + Infrastructure ─── */}
        <div className="admin-grid admin-animate-3">
          {/* Audit & Compliance */}
          <section className="admin-panel" id="audit-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--audit">🛡️</div>
                <span className="admin-panel__title">Audit & Compliance Monitoring</span>
              </div>
              <StatusTag status="enabled" label="Encrypted" />
            </div>
            <div className="admin-panel__body">
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Total Logins Today</span>
                <span className="admin-metric-row__value">{data.audit.totalLogins}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Failed Login Attempts</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.audit.failedLogins > 5 ? 'red' : data.audit.failedLogins > 2 ? 'amber' : 'green'} />
                  {data.audit.failedLogins}
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Data Access Logs</span>
                <span className="admin-metric-row__value">{data.audit.dataAccessLogs.toLocaleString()}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Sensitive Record Access</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.audit.sensitiveAccess > 10 ? 'amber' : 'green'} />
                  {data.audit.sensitiveAccess}
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Last Backup</span>
                <span className="admin-metric-row__value">{data.audit.lastBackup}</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Encryption Status</span>
                <span className="admin-metric-row__value">
                  <StatusTag status="enabled" label="AES-256 Enabled" />
                </span>
              </div>
              <button id="admin-export-audit" className="admin-export-btn" onClick={() => alert('Audit trail export initiated.')}>
                📥 Export Audit Trail
              </button>
            </div>
          </section>

          {/* AWS & Infrastructure Health */}
          <section className="admin-panel" id="infra-panel">
            <div className="admin-panel__header">
              <div className="admin-panel__title-group">
                <div className="admin-panel__icon admin-panel__icon--infra">☁️</div>
                <span className="admin-panel__title">AWS & Infrastructure Health</span>
              </div>
              <span className="admin-panel__badge">{data.infra.uptime}% Uptime</span>
            </div>
            <div className="admin-panel__body">
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">RDS Status</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.infra.rds} label={data.infra.rds === 'healthy' ? 'Healthy' : 'Degraded'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Bedrock Integration</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.infra.bedrock} label={data.infra.bedrock === 'healthy' ? 'Connected' : 'Degraded'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">MCP Server Status</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.infra.mcp} label={data.infra.mcp === 'healthy' ? 'Online' : 'Degraded'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">API Gateway Health</span>
                <span className="admin-metric-row__value">
                  <StatusTag status={data.infra.apiGateway} label={data.infra.apiGateway === 'healthy' ? 'Healthy' : 'Degraded'} />
                </span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">System Uptime</span>
                <span className="admin-metric-row__value">{data.infra.uptime}%</span>
              </div>
              <div className="admin-metric-row">
                <span className="admin-metric-row__label">Avg Response Time</span>
                <span className="admin-metric-row__value">
                  <StatusDot status={data.infra.avgResponseMs > 200 ? 'red' : data.infra.avgResponseMs > 150 ? 'amber' : 'green'} />
                  {data.infra.avgResponseMs}ms
                </span>
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* ═══ Footer ═══ */}
      <footer className="admin-dashboard__footer">
        CDSS Admin Console · Read-Only View · Role-Based Access Enforced · Data refreshes every 30s
      </footer>
    </div>
  );
}
