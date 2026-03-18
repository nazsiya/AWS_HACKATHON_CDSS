import { useOutletContext } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patients } from '../../data/mockData';
import { adherenceLabel, doseStatusLabel, normalizeDoseStatus, t } from '../../components/PatientPortal/i18n';
import './PatientPortalPages.css';

function formatDateTime(value) {
    if (!value) return '—';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function Tag({ variant, value }) {
    if (!value) return null;
    return <span className={`patient-portal-tag patient-portal-tag--${variant || 'neutral'}`}>{value}</span>;
}

function ProgressBar({ value }) {
    const pct = Math.max(0, Math.min(100, Number(value) || 0));
    return (
        <div className="patient-portal-meter" aria-label={`Progress ${pct}%`}>
            <div className="patient-portal-meter__bar" style={{ width: `${pct}%` }} />
            <span className="patient-portal-meter__text">{pct}%</span>
        </div>
    );
}

export default function PatientPortalHome() {
    const { user } = useAuth();
    const { language } = useOutletContext() || { language: 'en' };
    const patientId = user?.id;
    const patientEmail = (user?.email || '').toLowerCase();
    // Match by id first, then by email (so demo login always finds the right record)
    const patient = patients.find((p) => p.id === patientId) ||
        patients.find((p) => (p.email || '').toLowerCase() === patientEmail) ||
        patients[0] || null;
    const portal = patient?.portal || {};

    const adherencePct = patient?.adherence != null ? Math.round((patient.adherence || 0) * 100) : null;
    const weeklyAdherencePct = portal?.weeklyAdherence != null ? Math.round((portal.weeklyAdherence || 0) * 100) : (adherencePct ?? 0);

    const todayMeds = Array.isArray(portal?.todayMedications) ? portal.todayMedications : [];
    const upcomingAppts = Array.isArray(portal?.appointments?.upcoming) ? portal.appointments.upcoming : [];
    const nextAppt = patient?.nextAppointment || upcomingAppts?.[0]?.dateTime || null;
    const nextApptDoctor = patient?.nextAppointmentDetails?.doctorName || upcomingAppts?.[0]?.doctorName || '—';
    const nextApptDept = patient?.nextAppointmentDetails?.department || upcomingAppts?.[0]?.department || null;

    return (
        <div className="patient-portal-page">
            <h1 className="patient-portal-page__title">{t(language, 'dashboard_title')}</h1>
            <p className="patient-portal-page__welcome">
                {t(language, 'dashboard_welcome', { name: user?.name || '' })}
                <span className="patient-portal-inline-muted">
                    {t(language, 'label_language')}: {language?.toUpperCase?.() || 'EN'}
                </span>
            </p>

            <div className="patient-portal-cards">
                <div className="patient-portal-card">
                    <h2 className="patient-portal-card__title">{t(language, 'dashboard_nextAppt')}</h2>
                    <div className="patient-portal-card__value">{formatDateTime(nextAppt)}</div>
                    <div className="patient-portal-card__sub">
                        <span>{nextApptDoctor}</span>
                        {nextApptDept ? <span className="patient-portal-inline-muted">• {nextApptDept}</span> : null}
                    </div>
                </div>

                <div className="patient-portal-card">
                    <h2 className="patient-portal-card__title">{t(language, 'dashboard_activeRx')}</h2>
                    <div className="patient-portal-card__value">{portal?.activePrescriptionsCount ?? '—'}</div>
                </div>

                <div className="patient-portal-card">
                    <h2 className="patient-portal-card__title">{t(language, 'dashboard_adherence')}</h2>
                    <p className="patient-portal-card__value">
                        {adherencePct != null ? `${adherencePct}%` : '—'}{' '}
                        <Tag
                            variant={(() => {
                                const v = String(portal?.medicationAdherenceStatus || '').toLowerCase();
                                if (v.includes('excellent') || v.includes('good')) return 'success';
                                if (v.includes('low') || v.includes('need')) return 'danger';
                                return 'neutral';
                            })()}
                            value={adherenceLabel(language, portal?.medicationAdherenceStatus)}
                        />
                    </p>
                </div>

                <div className="patient-portal-card">
                    <h2 className="patient-portal-card__title">{t(language, 'dashboard_visitSummaryStatus')}</h2>
                    <div className="patient-portal-card__value">
                        <Tag
                            variant={portal?.aiVisitSummary?.available ? 'success' : 'neutral'}
                            value={portal?.aiVisitSummary?.available ? t(language, 'status_available') : t(language, 'status_notAvailable')}
                        />
                    </div>
                    <div className="patient-portal-card__sub patient-portal-inline-muted">{t(language, 'dashboard_aiSummaryHint')}</div>
                </div>
            </div>

            <div className="patient-portal-section">
                <div className="patient-portal-section__head">
                    <h2 className="patient-portal-section__title">{t(language, 'dashboard_weeklyMeter')}</h2>
                </div>
                <ProgressBar value={weeklyAdherencePct} />
            </div>

            <div className="patient-portal-grid-2">
                <div className="patient-portal-section">
                    <div className="patient-portal-section__head">
                        <h2 className="patient-portal-section__title">{t(language, 'dashboard_todaysMeds')}</h2>
                    </div>
                    {todayMeds.length === 0 ? (
                        <div className="patient-portal-empty">{t(language, 'empty_noTodaysMeds')}</div>
                    ) : (
                        <ul className="patient-portal-today">
                            {todayMeds.map((m) => (
                                <li key={m.id || `${m.medicine}-${m.time}`} className="patient-portal-today__item">
                                    <div className="patient-portal-today__main">
                                        <div className="patient-portal-today__name">
                                            {m.medicine} <span className="patient-portal-inline-muted">{m.dosage}</span>
                                        </div>
                                        <div className="patient-portal-today__meta">
                                            <span className="patient-portal-inline-muted">Scheduled: {m.time || '—'}</span>
                                        </div>
                                    </div>
                                    <div className="patient-portal-today__status">
                                        <Tag
                                            variant={(() => {
                                                const code = normalizeDoseStatus(m.status);
                                                return code === 'taken' ? 'success' : code === 'missed' ? 'danger' : 'warning';
                                            })()}
                                            value={doseStatusLabel(language, m.status)}
                                        />
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div className="patient-portal-section">
                    <div className="patient-portal-section__head">
                        <h2 className="patient-portal-section__title">{t(language, 'dashboard_upcomingAppts')}</h2>
                    </div>
                    {upcomingAppts.length === 0 ? (
                        <div className="patient-portal-empty">{t(language, 'empty_noUpcomingAppts')}</div>
                    ) : (
                        <ul className="patient-portal-appts">
                            {upcomingAppts.map((a) => (
                                <li key={a.id || a.dateTime} className="patient-portal-appts__item">
                                    <div className="patient-portal-appts__top">
                                        <span className="patient-portal-appts__doctor">{a.doctorName || '—'}</span>
                                        <span className="patient-portal-inline-muted">{a.department || ''}</span>
                                    </div>
                                    <div className="patient-portal-appts__dt">{formatDateTime(a.dateTime)}</div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}
