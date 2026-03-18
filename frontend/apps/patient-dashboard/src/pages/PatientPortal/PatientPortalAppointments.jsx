import { Link, useOutletContext } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patients } from '../../data/mockData';
import { t } from '../../components/PatientPortal/i18n';
import './PatientPortalPages.css';

function formatDateTime(value) {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function PatientPortalAppointments() {
    const { user } = useAuth();
    const { language } = useOutletContext() || { language: 'en' };
    const patient = patients.find((p) => p.id === user?.id) ||
        patients.find((p) => (p.email || '').toLowerCase() === (user?.email || '').toLowerCase()) ||
        patients[0] || null;
    const appts = patient?.portal?.appointments || {};
    const upcoming = Array.isArray(appts?.upcoming) ? appts.upcoming : [];
    const past = Array.isArray(appts?.past) ? appts.past : [];

    return (
        <div className="patient-portal-page">
            <h1 className="patient-portal-page__title">{t(language, 'appts_title')}</h1>
            <p className="patient-portal-page__desc">
                {t(language, 'appts_desc')}{' '}
                <span className="patient-portal-inline-muted">{t(language, 'label_language')}:</span> {String(language || 'en').toUpperCase()}
            </p>

            <div className="patient-portal-grid-2">
                <div className="patient-portal-section">
                    <div className="patient-portal-section__head">
                        <h2 className="patient-portal-section__title">{t(language, 'appts_upcoming')}</h2>
                    </div>
                    {upcoming.length === 0 ? (
                        <div className="patient-portal-empty">{t(language, 'appts_noneUpcoming')}</div>
                    ) : (
                        <ul className="patient-portal-appts">
                            {upcoming.map((a) => (
                                <li key={a.id || a.dateTime} className="patient-portal-appts__item">
                                    <div className="patient-portal-appts__top">
                                        <span className="patient-portal-appts__doctor">{a.doctorName || '—'}</span>
                                        <span className="patient-portal-inline-muted">{a.department || ''}</span>
                                    </div>
                                    {a.clinicalNotes ? (
                                        <div className="patient-portal-inline-muted" style={{ marginTop: 4 }}>{a.clinicalNotes}</div>
                                    ) : null}
                                    <div className="patient-portal-appts__dt">{formatDateTime(a.dateTime)}</div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div className="patient-portal-section">
                    <div className="patient-portal-section__head">
                        <h2 className="patient-portal-section__title">{t(language, 'appts_past')}</h2>
                    </div>
                    {past.length === 0 ? (
                        <div className="patient-portal-empty">{t(language, 'appts_nonePast')}</div>
                    ) : (
                        <ul className="patient-portal-appts">
                            {past.map((v) => (
                                <li key={v.id || v.dateTime} className="patient-portal-appts__item">
                                    <div className="patient-portal-appts__top">
                                        <span className="patient-portal-appts__doctor">{v.doctorName || '—'}</span>
                                        <span className="patient-portal-inline-muted">{v.department || ''}</span>
                                    </div>
                                    <div className="patient-portal-appts__dt">{formatDateTime(v.dateTime)}</div>
                                    <div style={{ marginTop: 'var(--space-2)' }}>
                                        {v.summaryAvailable ? (
                                            <Link to="/summary" className="patient-portal-link-btn">
                                                {t(language, 'appts_summaryAccess')}
                                            </Link>
                                        ) : (
                                            <span className="patient-portal-inline-muted">{t(language, 'appts_summaryNotAvailable')}</span>
                                        )}
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}

