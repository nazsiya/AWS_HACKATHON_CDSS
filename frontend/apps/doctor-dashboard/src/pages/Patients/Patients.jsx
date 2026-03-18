import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { isMockMode } from '../../api/config';
import { getPatients } from '../../api/client';
import { patients } from '../../data/mockData';
import { useActivity } from '../../context/ActivityContext';
import './Patients.css';

const getInitials = (name) => name.split(' ').map(n => n[0]).join('');

const filters = ['All', 'Critical', 'High', 'Moderate', 'Low'];

export default function Patients() {
    const [activeFilter, setActiveFilter] = useState('All');
    const [list, setList] = useState(isMockMode() ? patients : []);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedPatient, setSelectedPatient] = useState(null);
    const [loading, setLoading] = useState(!isMockMode());
    const [error, setError] = useState(null);
    const navigate = useNavigate();
    const { logActivity } = useActivity();

    useEffect(() => {
        logActivity('view_patient_list');
    }, [logActivity]);

    useEffect(() => {
        if (isMockMode()) {
            setList(patients);
            return;
        }
        let cancelled = false;
        setLoading(true);
        setError(null);
        getPatients()
            .then((data) => {
                if (cancelled) return;
                setList(Array.isArray(data) ? data : (data.patients || data.items || []));
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load patients');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, []);

    const filtered = activeFilter === 'All'
        ? list
        : list.filter(p => (p.severity || '').toLowerCase() === activeFilter.toLowerCase());

    const searchFiltered = !searchQuery.trim()
        ? filtered
        : filtered.filter((p) => {
            const q = searchQuery.trim().toLowerCase();
            const name = (p.name || '').toLowerCase();
            const id = (p.id || '').toLowerCase();
            const ward = (p.ward || '').toLowerCase();
            const bloodGroup = (p.bloodGroup || '').toLowerCase();
            const severity = (p.severity || '').toLowerCase();
            const status = (p.status || '').toLowerCase();
            const lastVisit = (p.lastVisit || '').toLowerCase();
            const conditionsStr = (Array.isArray(p.conditions) ? p.conditions : [p.conditions]).filter(Boolean).join(' ').toLowerCase();
            const ageStr = p.age != null ? String(p.age) : '';
            return name.includes(q) || id.includes(q) || ward.includes(q) || bloodGroup.includes(q) ||
                severity.includes(q) || status.includes(q) || lastVisit.includes(q) || conditionsStr.includes(q) || ageStr.includes(q);
        });

    const riskScore = (p) => {
        const s = (p.severity || '').toLowerCase();
        if (s === 'critical') return 8;
        if (s === 'high') return 6;
        if (s === 'moderate') return 4;
        if (s === 'low') return 2;
        return 5;
    };

    const aiSummaryForPatient = selectedPatient || searchFiltered[0];

    if (loading && !isMockMode()) {
        return (
            <div className="patients-page page-enter" style={{ padding: '2rem', textAlign: 'center' }}>
                <p>Loading patients…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="patients-page page-enter" style={{ padding: '2rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-error, #c00)' }}>{error}</p>
                <button
                    className="btn btn--primary"
                    onClick={() => {
                        setError(null);
                        setLoading(true);
                        getPatients()
                            .then((data) => setList(Array.isArray(data) ? data : (data.patients || data.items || [])))
                            .catch((err) => setError(err.message || 'Failed to load patients'))
                            .finally(() => setLoading(false));
                    }}
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="patients-page page-enter">
            <div className="patients-page__header">
                <h1 className="patients-page__title">Patient Search</h1>
                <div className="patients-page__search-engine">
                    <label className="patients-search-wrap" htmlFor="patients-search-input">
                        <span className="patients-search-wrap__icon" aria-hidden="true">🔍</span>
                        <input
                            id="patients-search-input"
                            type="text"
                            className="patients-search-input"
                            placeholder="Search by ID, name, ward, condition, severity..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            aria-label="Search patients by ID, name, ward, condition, or severity"
                        />
                        {searchQuery.length > 0 && (
                            <button
                                type="button"
                                className="patients-search-wrap__clear"
                                onClick={(e) => { e.preventDefault(); setSearchQuery(''); }}
                                aria-label="Clear search"
                            >
                                ✕
                            </button>
                        )}
                    </label>
                </div>
                <div className="patients-page__filters">
                    {filters.map(f => (
                        <button
                            key={f}
                            className={`filter-btn ${activeFilter === f ? 'active' : ''}`}
                            onClick={() => setActiveFilter(f)}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            <div className="patients-page__content">
                <div className="patients-quick-cards">
                    {searchFiltered.map((p) => (
                        <div
                            key={p.id}
                            className={`patient-quick-card ${selectedPatient?.id === p.id ? 'selected' : ''}`}
                            onClick={() => { setSelectedPatient(p); navigate(`/patient/${p.id}`); }}
                        >
                            <div className="patient-quick-card__meta">
                                <span className="patient-quick-card__name">{p.name}</span>
                                <span className="patient-quick-card__id">ID: {p.id}</span>
                                <span className="patient-quick-card__demog">{p.age != null ? `${p.age}y` : '—'} / {(p.gender || 'M')[0]} · {p.bloodGroup || '—'}</span>
                            </div>
                            <div className="patient-quick-card__risk">
                                <span className="patient-quick-card__risk-label">Clinical Risk</span>
                                <span className="patient-quick-card__risk-value">{riskScore(p)}/10</span>
                            </div>
                            <div className="patient-quick-card__conditions">
                                {(Array.isArray(p.conditions) ? p.conditions : [p.conditions]).filter(Boolean).slice(0, 3).map((c, i) => (
                                    <span key={i} className="patient-quick-card__tag">{c}</span>
                                ))}
                            </div>
                            <div className="patient-quick-card__last-visit">Last visit: {p.lastVisit || '—'}</div>
                        </div>
                    ))}
                </div>

                {aiSummaryForPatient && (
                    <div className="patients-ai-summary-panel">
                        <h3 className="patients-ai-summary-panel__title">AI-Generated Clinical Summary</h3>
                        <div className="patients-ai-summary-panel__section">
                            <h4>Major Diagnoses</h4>
                            <p>{(Array.isArray(aiSummaryForPatient.conditions) ? aiSummaryForPatient.conditions : [aiSummaryForPatient.conditions]).filter(Boolean).join('; ') || '—'}</p>
                        </div>
                        <div className="patients-ai-summary-panel__section">
                            <h4>Treatment Plan</h4>
                            <p>Current AI-suggested regime: {(aiSummaryForPatient.conditions || [])[0] ? `Focus on ${(aiSummaryForPatient.conditions || [])[0]} management; medication review as per last visit.` : '—'}</p>
                        </div>
                        <div className="patients-ai-summary-panel__section">
                            <h4>Risk Factors</h4>
                            <p>{(aiSummaryForPatient.surgeryReadiness?.riskFactors || []).length > 0 ? aiSummaryForPatient.surgeryReadiness.riskFactors.join('; ') : 'Allergies and comorbidities per record. Monitor vitals.'}</p>
                        </div>
                        <div className="patients-ai-summary-panel__section">
                            <h4>Recommended Follow-Up</h4>
                            <p>{aiSummaryForPatient.nextAppointment ? `Next appointment scheduled. Recheck vitals and labs at next visit.` : 'Schedule follow-up as clinically indicated.'}</p>
                        </div>
                        <button type="button" className="btn btn--primary" onClick={() => navigate(`/patient/${aiSummaryForPatient.id}`)}>Open full record →</button>
                    </div>
                )}
            </div>

            <div className="patients-table animate-in">
                <table>
                    <thead>
                        <tr>
                            <th>Patient</th>
                            <th>Patient ID</th>
                            <th>Age / Gender</th>
                            <th>Ward</th>
                            <th>Conditions</th>
                            <th>Vitals</th>
                            <th>Severity</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {searchFiltered.map((p, i) => (
                            <tr key={p.id} className={`animate-in animate-in-delay-${Math.min(i + 1, 6)}`} onClick={() => navigate(`/patient/${p.id}`)}>
                                <td>
                                    <div className="patient-name-cell">
                                        <div className={`patient-name-cell__avatar queue-item__avatar--${(p.gender || 'male').toLowerCase()}`}>
                                            {getInitials(p.name)}
                                        </div>
                                        <div className="patient-name-cell__text">
                                            <span className="patient-name-cell__name">{p.name}</span>
                                        </div>
                                    </div>
                                </td>
                                <td><span className="mono" style={{ fontSize: 'var(--text-sm)' }}>{p.id}</span></td>
                                <td>{p.age != null ? `${p.age}y` : '—'} / {(p.gender || 'M')[0]}</td>
                                <td>{p.ward || '—'}</td>
                                <td>{Array.isArray(p.conditions) ? p.conditions.join(', ') : (p.conditions || '—')}</td>
                                <td>
                                    <span className="mono" style={{ fontSize: 'var(--text-xs)' }}>
                                        HR:{p.vitals?.hr ?? '—'} BP:{p.vitals?.bp ?? '—'} O₂:{p.vitals?.spo2 ?? '—'}%
                                    </span>
                                </td>
                                <td>
                                    <span className={`queue-item__severity severity--${(p.severity || 'moderate').toLowerCase()}`}>{p.severity || '—'}</span>
                                </td>
                                <td>
                                    <span className={`schedule-item__status status--${p.status === 'in-consultation' ? 'in-progress' : p.status === 'waiting' ? 'upcoming' : 'completed'}`}>
                                        {(p.status || '—').replace('-', ' ')}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
