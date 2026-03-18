import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useActivity } from '../../context/ActivityContext';
import './MyActivity.css';

const actionLabels = {
  view_dashboard: 'Viewed Dashboard',
  view_patient_list: 'Viewed Patient List',
  view_patient: 'Viewed Patient Record',
  start_consultation: 'Started Consultation',
  save_consultation: 'Saved Consultation Notes',
  ai_chat: 'Used AI Assistant',
  ai_chat_patient: 'Used AI in Patient Consultation',
  view_medications: 'Viewed Medications',
  view_surgery: 'Viewed Surgery',
  view_activity: 'Viewed My Activity',
};

export default function MyActivity() {
  const { user } = useAuth();
  const { recentActivity } = useActivity();
  const navigate = useNavigate();

  return (
    <div className="my-activity-page page-enter">
      <div className="my-activity-page__header">
        <h1 className="my-activity-page__title">📋 My Activity</h1>
        <p className="my-activity-page__desc">
          Doctor_ID-linked history for {user?.name}. All healthcare provider actions are recorded here (Acceptance Criteria 4).
        </p>
      </div>

      <div className="my-activity-page__list">
        {recentActivity.length === 0 ? (
          <div className="my-activity-page__empty">
            <span className="my-activity-page__empty-icon">📭</span>
            <p>No activity recorded yet. Use the dashboard, open a patient, or use the AI assistant to see entries here.</p>
          </div>
        ) : (
          <ul className="activity-timeline">
            {recentActivity.map((entry) => (
              <li key={entry.id} className="activity-timeline__item">
                <div className="activity-timeline__dot" />
                <div className="activity-timeline__content">
                  <span className="activity-timeline__action">
                    {actionLabels[entry.type] || entry.type.replace(/_/g, ' ')}
                  </span>
                  {entry.patientId && (
                    <span className="activity-timeline__patient">
                      Patient ID: <button type="button" className="activity-timeline__link" onClick={() => navigate(`/patient/${entry.patientId}`)}>{entry.patientId}</button>
                    </span>
                  )}
                  {entry.detail && <span className="activity-timeline__detail">{entry.detail}</span>}
                  <span className="activity-timeline__time">
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
