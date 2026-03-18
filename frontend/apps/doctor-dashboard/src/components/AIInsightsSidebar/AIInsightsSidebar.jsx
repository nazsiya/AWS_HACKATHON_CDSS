import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './AIInsightsSidebar.css';

const mockRiskScore = 6;
const mockSeverityTag = 'HIGH';
const mockRecommendations = [
  { id: 1, title: 'Warfarin + Aspirin interaction', detail: 'Lakshmi Devi — high bleeding risk. Review combination.', type: 'Error' },
  { id: 2, title: 'SpO2 below target', detail: 'Mohammed Farhan — consider oxygen supplementation.', type: 'Warning' },
  { id: 3, title: 'HbA1c above target', detail: 'Rajesh Kumar — 7.8%. Consider medication adjustment.', type: 'Info' },
];
const mockAgents = [
  { name: 'Clinical AI', status: 'Connected' },
  { name: 'Surgical AI', status: 'Connected' },
  { name: 'Resource AI', status: 'Connected' },
];

export default function AIInsightsSidebar() {
  const [open, setOpen] = useState(true);
  const navigate = useNavigate();

  return (
    <aside className={`ai-insights-sidebar ${open ? 'open' : 'closed'}`}>
      <button
        type="button"
        className="ai-insights-sidebar__toggle"
        onClick={() => setOpen(!open)}
        title={open ? 'Collapse' : 'Expand'}
      >
        {open ? '▶' : '◀'}
      </button>
      {open && (
        <>
          <div className="ai-insights-sidebar__header">
            <h3 className="ai-insights-sidebar__title">AI Insights</h3>
          </div>

          {/* Global Risk Pulse */}
          <div className="ai-insights-block">
            <h4 className="ai-insights-block__label">Global Risk Pulse</h4>
            <div className="risk-pulse">
              <span className="risk-pulse__score">{mockRiskScore}</span>
              <span className="risk-pulse__max">/10</span>
              <span className={`risk-pulse__tag risk-pulse__tag--${mockSeverityTag.toLowerCase()}`}>
                {mockSeverityTag}
              </span>
            </div>
          </div>

          {/* Live Recommendations */}
          <div className="ai-insights-block">
            <h4 className="ai-insights-block__label">Live Recommendations</h4>
            <ul className="ai-insights-list">
              {mockRecommendations.map((rec) => (
                <li key={rec.id} className={`ai-insights-item ai-insights-item--${rec.type.toLowerCase()}`}>
                  <span className="ai-insights-item__title">{rec.title}</span>
                  <span className="ai-insights-item__detail">{rec.detail}</span>
                  <span className="ai-insights-item__type">{rec.type}</span>
                </li>
              ))}
            </ul>
            <button type="button" className="ai-insights-more" onClick={() => navigate('/alerts')}>
              View all in Alerts Center →
            </button>
          </div>

          {/* Agent Connectivity */}
          <div className="ai-insights-block">
            <h4 className="ai-insights-block__label">Agent Connectivity</h4>
            <ul className="agent-list">
              {mockAgents.map((agent) => (
                <li key={agent.name} className="agent-list__item">
                  <span className="agent-list__dot agent-list__dot--connected" />
                  <span>{agent.name}</span>
                  <span className="agent-list__status">{agent.status}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </aside>
  );
}
