import { useState, useEffect } from 'react';
import { isMockMode } from '../../api/config';
import { aiAlerts } from '../../data/mockData';
import './Alerts.css';

const severityTypes = ['Critical', 'Warning', 'Info', 'Success'];
const categoryLabels = {
  drug_interaction: 'Drug Interaction',
  vital_alert: 'Vital Alert',
  vital_abnormality: 'Vital Abnormality',
  lab_results: 'Lab Results',
  surgery: 'Surgery',
  adherence: 'Adherence',
  system: 'System',
  critical: 'Critical',
  warning: 'Warning',
  info: 'Info',
  success: 'Success',
};

export default function Alerts() {
  const [alerts, setAlerts] = useState(isMockMode() ? aiAlerts : []);
  const [loading, setLoading] = useState(!isMockMode());
  const [dismissed, setDismissed] = useState(new Set());
  const [filterSeverity, setFilterSeverity] = useState('All');

  useEffect(() => {
    if (!isMockMode()) {
      setLoading(false);
      setAlerts([]);
    }
  }, []);

  const criticalCount = alerts.filter((a) => (a.type || '').toLowerCase() === 'critical').length;
  const warningCount = alerts.filter((a) => (a.type || '').toLowerCase() === 'warning').length;

  const filtered =
    filterSeverity === 'All'
      ? alerts
      : alerts.filter((a) => (a.type || '').toLowerCase() === filterSeverity.toLowerCase());

  const visible = filtered.filter((a) => !dismissed.has(a.id));

  const handleDismiss = (id) => setDismissed((s) => new Set(s).add(id));
  const handleAction = (id) => {
    handleDismiss(id);
    // Could navigate to patient or open modal
  };

  return (
    <div className="alerts-page page-enter">
      <h1 className="alerts-page__title">🔔 Alerts Center</h1>
      <p className="alerts-page__desc">Global Alert Notification Center — severity triage and actionable alerts.</p>

      {/* Severity Triage */}
      <div className="alerts-triage">
        <button
          className={`alerts-triage__btn ${filterSeverity === 'Critical' ? 'active' : ''}`}
          onClick={() => setFilterSeverity('Critical')}
        >
          <span className="alerts-triage__count alerts-triage__count--critical">{criticalCount}</span>
          <span>Critical</span>
        </button>
        <button
          className={`alerts-triage__btn ${filterSeverity === 'Warning' ? 'active' : ''}`}
          onClick={() => setFilterSeverity('Warning')}
        >
          <span className="alerts-triage__count alerts-triage__count--warning">{warningCount}</span>
          <span>Warning</span>
        </button>
        <button
          className={`alerts-triage__btn ${filterSeverity === 'All' ? 'active' : ''}`}
          onClick={() => setFilterSeverity('All')}
        >
          <span className="alerts-triage__count">{alerts.length}</span>
          <span>All</span>
        </button>
      </div>

      {/* Alert Log */}
      <div className="alerts-log">
        {loading ? (
          <p>Loading alerts…</p>
        ) : visible.length === 0 ? (
          <p className="alerts-log__empty">No alerts to show.</p>
        ) : (
          visible.map((alert) => (
            <div
              key={alert.id}
              className={`alert-log-item alert-log-item--${(alert.type || 'info').toLowerCase()}`}
            >
              <div className="alert-log-item__main">
                <span className="alert-log-item__title">{alert.title}</span>
                {alert.patient && alert.patient !== '—' && (
                  <span className="alert-log-item__patient">Patient: {alert.patient}</span>
                )}
                <span className="alert-log-item__category">
                  {categoryLabels[(alert.type || '').toLowerCase()] || alert.type || 'Notification'}
                </span>
              </div>
              <div className="alert-log-item__meta">
                <span className="alert-log-item__time">{alert.time}</span>
                <div className="alert-log-item__actions">
                  <button type="button" className="btn btn--outline btn--sm" onClick={() => handleAction(alert.id)}>
                    Action
                  </button>
                  <button type="button" className="btn btn--ghost btn--sm" onClick={() => handleDismiss(alert.id)}>
                    Dismiss
                  </button>
                </div>
              </div>
              <div className="alert-log-item__message">{alert.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
