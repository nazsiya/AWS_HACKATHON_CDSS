import { useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patients } from '../../data/mockData';
import { doseStatusLabel, normalizeDoseStatus, t } from '../../components/PatientPortal/i18n';
import './PatientPortalPages.css';

function Tag({ language, value }) {
    if (!value) return null;
    const code = normalizeDoseStatus(value);
    const variant = code === 'taken' ? 'success' : code === 'missed' ? 'danger' : 'warning';
    return <span className={`patient-portal-tag patient-portal-tag--${variant}`}>{doseStatusLabel(language, value)}</span>;
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

export default function PatientPortalMedications() {
    const { user } = useAuth();
    const { language } = useOutletContext() || { language: 'en' };
    const patient = patients.find((p) => p.id === user?.id) ||
        patients.find((p) => (p.email || '').toLowerCase() === (user?.email || '').toLowerCase()) ||
        patients[0] || null;
    const todayMeds = Array.isArray(patient?.portal?.todayMedications) ? patient.portal.todayMedications : [];

    const [overrides, setOverrides] = useState({});
    const rows = useMemo(() => {
        return todayMeds.map((m) => {
            const status = overrides[m.id] || m.status || 'Pending';
            return { ...m, status };
        });
    }, [todayMeds, overrides]);

    const total = rows.length;
    const completed = rows.filter((r) => String(r.status).toLowerCase() === 'taken').length;
    const adherencePct = total > 0 ? Math.round((completed / total) * 100) : 0;

    const markTaken = (id) => {
        setOverrides((prev) => ({ ...prev, [id]: 'Taken' }));
    };

    return (
        <div className="patient-portal-page">
            <h1 className="patient-portal-page__title">{t(language, 'meds_title')}</h1>
            <p className="patient-portal-page__desc">
                {t(language, 'meds_desc')}{' '}
                <span className="patient-portal-inline-muted">{t(language, 'label_language')}:</span> {String(language || 'en').toUpperCase()}
            </p>

            <div className="patient-portal-section">
                <div className="patient-portal-section__head">
                    <h2 className="patient-portal-section__title">{t(language, 'meds_meterTitle')}</h2>
                    <div className="patient-portal-inline-muted">
                        {t(language, 'meds_doseCompletion', { completed, total })}
                    </div>
                </div>
                <ProgressBar value={adherencePct} />
            </div>

            <div className="patient-portal-section">
                <div className="patient-portal-section__head">
                    <h2 className="patient-portal-section__title">{t(language, 'meds_scheduleTitle')}</h2>
                </div>

                {rows.length === 0 ? (
                    <div className="patient-portal-empty">{t(language, 'meds_noneToday')}</div>
                ) : (
                    <div className="patient-portal-table-wrap">
                        <table className="patient-portal-table">
                            <thead>
                                <tr>
                                    <th>{t(language, 'table_medicine')}</th>
                                    <th>{t(language, 'table_dosage')}</th>
                                    <th>{t(language, 'table_time')}</th>
                                    <th>{t(language, 'table_status')}</th>
                                    <th>{t(language, 'table_action')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((r) => {
                                    const isTaken = String(r.status).toLowerCase() === 'taken';
                                    return (
                                        <tr key={r.id || `${r.medicine}-${r.time}`}>
                                            <td>{r.medicine || '—'}</td>
                                            <td className="patient-portal-inline-muted">{r.dosage || '—'}</td>
                                            <td>{r.time || '—'}</td>
                                            <td><Tag language={language} value={r.status} /></td>
                                            <td>
                                                {isTaken ? (
                                                    <span className="patient-portal-inline-muted">{t(language, 'meds_completed')}</span>
                                                ) : (
                                                    <button type="button" className="patient-portal-link-btn" onClick={() => markTaken(r.id)}>
                                                        {t(language, 'meds_markTaken')}
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
