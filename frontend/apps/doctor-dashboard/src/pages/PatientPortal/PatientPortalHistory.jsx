import { useAuth } from '../../context/AuthContext';
import { consultationHistory } from '../../data/mockData';
import './PatientPortalPages.css';

export default function PatientPortalHistory() {
    const { user } = useAuth();
    const patientId = user?.id;
    const history = (consultationHistory || []).filter((h) => h.patientId === patientId);

    return (
        <div className="patient-portal-page">
            <h1 className="patient-portal-page__title">My history</h1>
            <p className="patient-portal-page__desc">Your visit history and conversation summaries (your data only).</p>

            {history.length === 0 ? (
                <div className="patient-portal-empty">No visit history yet.</div>
            ) : (
                <ul className="patient-portal-history">
                    {history.map((entry, i) => (
                        <li key={entry.id || i} className="patient-portal-history__item">
                            <span className="patient-portal-history__date">{entry.date}</span>
                            <span className="patient-portal-history__doctor">{entry.doctor}</span>
                            {entry.aiSummary && (
                                <p className="patient-portal-history__summary">{entry.aiSummary}</p>
                            )}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
