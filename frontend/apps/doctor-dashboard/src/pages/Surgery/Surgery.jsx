import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth, roles } from '../../context/AuthContext';
import { isMockMode } from '../../api/config';
import { getSurgeries, analyseSurgery } from '../../api/client';
import { surgeries } from '../../data/mockData';
import './Surgery.css';

const columns = [
    { key: 'scheduled', label: 'Scheduled', variant: 'scheduled' },
    { key: 'in-prep', label: 'In Preparation', variant: 'in-prep' },
    { key: 'pre-op', label: 'Pre-Op Assessment', variant: 'pre-op' },
];

export default function Surgery() {
    const navigate = useNavigate();
    const location = useLocation();
    const { hasRole } = useAuth();
    const isSurgeon = hasRole(roles.SURGEON);
    const fromPatient = location.state?.patientId && location.state?.patientName;
    const [list, setList] = useState(isMockMode() ? surgeries : []);
    const [loading, setLoading] = useState(!isMockMode());
    const [error, setError] = useState(null);
    const [replacementFor, setReplacementFor] = useState(null);
    const [replacementNotified, setReplacementNotified] = useState(false);
    const [selectedPreOp, setSelectedPreOp] = useState(null);
    const [sessionRequirements, setSessionRequirements] = useState({});
    const [newItemTexts, setNewItemTexts] = useState({ equipment: '', checklist: '' });
    const [suggestionsLoading, setSuggestionsLoading] = useState(false);
    const [suggestionsError, setSuggestionsError] = useState(null);

    const mockReplacements = [
        { id: 'DR-ALT-1', name: 'Dr. Suresh Reddy', specialty: 'General Surgery', status: 'available' },
        { id: 'DR-ALT-2', name: 'Dr. Priya Sharma', specialty: 'General', status: 'available' },
    ];

    useEffect(() => {
        if (isMockMode()) {
            setList(surgeries);
            return;
        }
        let cancelled = false;
        setLoading(true);
        setError(null);
        getSurgeries()
            .then((data) => {
                if (cancelled) return;
                setList(Array.isArray(data) ? data : (data.surgeries || data.items || []));
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load surgeries');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, []);

    // When Pre-Op modal opens, fetch AI suggestions for this surgery (real API only)
    useEffect(() => {
        if (!selectedPreOp?.id || isMockMode()) return;
        setSuggestionsLoading(true);
        setSuggestionsError(null);
        analyseSurgery(selectedPreOp.id)
            .then((result) => {
                const equipment = (result.requiredInstruments || []).map((name) => ({ name: String(name), checked: false }));
                const checklist = (result.checklist || []).map((c) => ({
                    name: typeof c === 'string' ? c : (c.text || c.name || String(c)),
                    checked: !!(c && c.completed),
                }));
                setSessionRequirements((prev) => ({
                    ...prev,
                    [selectedPreOp.id]: {
                        equipment: equipment.length > 0 ? equipment : (prev[selectedPreOp.id]?.equipment || []),
                        checklist: checklist.length > 0 ? checklist : (prev[selectedPreOp.id]?.checklist || []),
                    },
                }));
            })
            .catch((err) => setSuggestionsError(err?.message || 'Could not load AI suggestions'))
            .finally(() => setSuggestionsLoading(false));
    }, [selectedPreOp?.id]);

    if (loading && !isMockMode()) {
        return (
            <div className="surgery-page page-enter" style={{ padding: '2rem', textAlign: 'center' }}>
                <p>Loading surgery queue…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="surgery-page page-enter" style={{ padding: '2rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-error, #c00)' }}>{error}</p>
                <button
                    className="btn btn--primary"
                    onClick={() => {
                        setError(null);
                        setLoading(true);
                        getSurgeries()
                            .then((data) => setList(Array.isArray(data) ? data : (data.surgeries || data.items || [])))
                            .catch((err) => setError(err.message || 'Failed to load surgeries'))
                            .finally(() => setLoading(false));
                    }}
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="surgery-page page-enter">
            <h1 className="surgery-page__title">🔪 Surgeries</h1>
            <p className="surgery-page__desc">
                {isSurgeon ? 'Surgical schedule, OT assignment, and complication simulation.' : 'View surgical schedule. Pre-op planning and OT assignment are available to surgeons.'}
            </p>

            {!isSurgeon && (
                <div className="surgery-page__role-note" style={{ padding: '12px 16px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '10px', marginBottom: '20px', fontSize: '14px', color: '#1e40af' }}>
                    You are viewing the surgical schedule. For consultation workflow and patient tasks, use <button type="button" className="link-btn" onClick={() => navigate('/patients')} style={{ background: 'none', border: 'none', color: '#2563eb', textDecoration: 'underline', cursor: 'pointer' }}>Patients</button> or <button type="button" className="link-btn" onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#2563eb', textDecoration: 'underline', cursor: 'pointer' }}>Dashboard</button>.
                </div>
            )}

            {/* Surgical Schedule Table */}
            <div className="surgery-schedule-table-wrap">
                <h2 className="surgery-section-title">Surgical Schedule Table</h2>
                <table className="surgery-schedule-table">
                    <thead>
                        <tr>
                            <th>Surgery name</th>
                            <th>Date / Time</th>
                            <th>Surgeon</th>
                            <th>OT assignment</th>
                            <th>Team</th>
                            <th>Duration</th>
                            <th>Status</th>
                            <th>Clinical Info</th>
                        </tr>
                    </thead>
                    <tbody>
                        {list.map((s) => (
                            <tr key={s.id}>
                                <td onClick={() => isSurgeon && navigate(`/surgery-planning/${s.id}`)} style={{ cursor: isSurgeon ? 'pointer' : 'default' }}>{s.type}</td>
                                <td>{s.date} {s.time}</td>
                                <td>{s.surgeon || '—'}</td>
                                <td>{s.ot || '—'}</td>
                                <td>Team —</td>
                                <td>{s.estimatedDuration || '—'}</td>
                                <td><span className={`surgery-status-tag surgery-status-tag--${(s.status || '').replace('-', '_')}`}>{s.status === 'in-prep' ? 'In Progress' : s.status === 'pre-op' ? 'Pre-Op Assessment' : (s.status || 'Scheduled')}</span></td>
                                <td>
                                    <button
                                        className="surgery-card__plan-btn"
                                        style={{ padding: '4px 8px', fontSize: '11px', margin: 0 }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setSelectedPreOp(s);
                                        }}
                                    >
                                        Pre-Op Info
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Complication Simulator - Surgeon only */}
            {isSurgeon && (
                <div className="surgery-complication-simulator">
                    <h2 className="surgery-section-title">Complication Simulator (Edge Case)</h2>
                    <div className="complication-simulator__card">
                        <div className="complication-simulator__row">
                            <span className="complication-simulator__label">Complication Type</span>
                            <span className="complication-simulator__value">Intraoperative findings — unexpected bleeding</span>
                        </div>
                        <div className="complication-simulator__row">
                            <span className="complication-simulator__label">AI Suggested Intervention</span>
                            <span className="complication-simulator__value">Real-time surgical guidance: Apply pressure, consider vessel ligation; check coagulation panel.</span>
                        </div>
                        <div className="complication-simulator__row">
                            <span className="complication-simulator__label">Immediate Actions</span>
                            <ol className="complication-simulator__actions">
                                <li>Maintain hemodynamics; request blood products if needed.</li>
                                <li>Identify source; consider intra-op imaging.</li>
                                <li>Follow emergency protocol for hemorrhage control.</li>
                            </ol>
                        </div>
                    </div>
                </div>
            )}

            {replacementFor && (
                <div className="surgery-replacement-panel" style={{ marginBottom: 'var(--space-5)', padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ marginBottom: 'var(--space-2)' }}>Find replacement — {replacementFor.type} ({replacementFor.id})</h3>
                    <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
                        Current: {replacementFor.surgeon}. Qualified replacements (Scheduling Agent):
                    </p>
                    <ul style={{ listStyle: 'none', padding: 0, marginBottom: 'var(--space-3)' }}>
                        {mockReplacements.map((r) => (
                            <li key={r.id} style={{ padding: 'var(--space-2)', background: 'var(--surface-bg)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-2)' }}>
                                {r.name} — {r.specialty} ({r.status})
                            </li>
                        ))}
                    </ul>
                    <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        <button
                            className="btn btn--primary"
                            onClick={() => { setReplacementNotified(true); setTimeout(() => { setReplacementFor(null); setReplacementNotified(false); }, 2000); }}
                            disabled={replacementNotified}
                        >
                            {replacementNotified ? 'Notified ✓' : 'Notify replacement & team'}
                        </button>
                        <button className="btn btn--outline" onClick={() => setReplacementFor(null)}>Cancel</button>
                    </div>
                </div>
            )}

            {fromPatient && (
                <div className="surgery-new-card" style={{ marginBottom: 'var(--space-5)', padding: 'var(--space-4)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 'var(--radius-lg)' }}>
                    <strong>New surgery requested for {location.state.patientName}</strong>
                    <p style={{ margin: 'var(--space-2) 0', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Create a surgery and open the planning flow to pick an OT slot.</p>
                    {isSurgeon && (
                        <button
                            className="btn btn--primary"
                            onClick={() => navigate('/surgery-planning/new', { state: { patientId: location.state.patientId, patientName: location.state.patientName }, replace: true })}
                        >
                            Create surgery & plan
                        </button>
                    )}
                </div>
            )}

            <div className="surgery-board">
                {columns.map((col, ci) => {
                    const items = list.filter(s => s.status === col.key);
                    return (
                        <div key={col.key} className={`surgery-column animate-in animate-in-delay-${ci + 1}`}>
                            <div className="surgery-column__header">
                                <div className={`surgery-column__dot surgery-column__dot--${col.variant}`} />
                                <span className="surgery-column__title">{col.label}</span>
                                <span className="surgery-column__count">{items.length}</span>
                            </div>
                            {items.map((surgery, i) => (
                                <div key={surgery.id} className={`surgery-card animate-in animate-in-delay-${i + 2}`}>
                                    <div className="surgery-card__id">{surgery.id}</div>
                                    <div className="surgery-card__type">{surgery.type}</div>
                                    <div className="surgery-card__patient">👤 {surgery.patient}</div>
                                    <div className="surgery-card__meta">
                                        <span className="surgery-card__meta-item">🏥 {surgery.ot || '—'}</span>
                                        <span className="surgery-card__meta-item">📅 {surgery.date || '—'}</span>
                                        <span className="surgery-card__meta-item">⏰ {surgery.time || '—'}</span>
                                    </div>
                                    <div style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                        🩺 {surgery.surgeon || '—'}
                                    </div>

                                    <button
                                        className="surgery-card__plan-btn"
                                        style={{ marginTop: 'var(--space-2)', background: '#6366f1', color: '#fff' }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setSelectedPreOp(surgery);
                                        }}
                                    >
                                        View Pre-Op Requirements
                                    </button>

                                    {(surgery.status === 'scheduled' || surgery.status === 'in-prep') && isSurgeon && (
                                        <>
                                            <button
                                                className="surgery-card__plan-btn"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    navigate(`/surgery-planning/${surgery.id}`);
                                                }}
                                            >
                                                Plan Procedure
                                            </button>
                                            <button
                                                className="surgery-card__plan-btn"
                                                style={{ marginTop: 'var(--space-1)', background: 'var(--surface-card)', border: '1px solid var(--surface-border)', color: 'var(--text-primary)' }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setReplacementFor(surgery);
                                                }}
                                            >
                                                Doctor unavailable? Find replacement
                                            </button>
                                        </>
                                    )}
                                </div>
                            ))}
                            {items.length === 0 && (
                                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
                                    No surgeries
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Pre-Op Requirements Modal */}
            {selectedPreOp && (() => {
                const sId = selectedPreOp.id;
                // Initialize or get session-specific data for this surgery
                const existing = sessionRequirements[sId];
                const defaultEquipment = (selectedPreOp.preOpRequirements?.equipment || []).map(name => ({ name, checked: false }));
                const defaultChecklist = (selectedPreOp.preOpRequirements?.checklist || []).map(name => ({ name, checked: false }));
                const sessionData = existing || {
                    equipment: defaultEquipment,
                    checklist: defaultChecklist
                };

                const fetchSuggestions = () => {
                    if (!sId || isMockMode()) return;
                    setSuggestionsLoading(true);
                    setSuggestionsError(null);
                    analyseSurgery(sId)
                        .then((result) => {
                            const equipment = (result.requiredInstruments || []).map((name) => ({ name: String(name), checked: false }));
                            const checklist = (result.checklist || []).map((c) => ({
                                name: typeof c === 'string' ? c : (c.text || c.name || String(c)),
                                checked: !!(c && c.completed),
                            }));
                            setSessionRequirements((prev) => ({
                                ...prev,
                                [sId]: {
                                    equipment: equipment.length > 0 ? equipment : prev[sId]?.equipment || [],
                                    checklist: checklist.length > 0 ? checklist : prev[sId]?.checklist || [],
                                },
                            }));
                        })
                        .catch((err) => setSuggestionsError(err?.message || 'Could not load AI suggestions'))
                        .finally(() => setSuggestionsLoading(false));
                };

                const toggleItem = (type, index) => {
                    const newData = { ...sessionData };
                    newData[type][index].checked = !newData[type][index].checked;
                    setSessionRequirements({ ...sessionRequirements, [sId]: newData });
                };

                const addItem = (type) => {
                    const text = newItemTexts[type].trim();
                    if (!text) return;
                    const newData = { ...sessionData };
                    newData[type].push({ name: text, checked: false });
                    setSessionRequirements({ ...sessionRequirements, [sId]: newData });
                    setNewItemTexts({ ...newItemTexts, [type]: '' });
                };

                return (
                    <div className="pre-op-modal-overlay" onClick={() => setSelectedPreOp(null)}>
                        <div className="pre-op-modal" onClick={e => e.stopPropagation()}>
                            <div className="pre-op-modal__header">
                                <div>
                                    <h3 className="pre-op-modal__title">Pre-Op Planning Checklist</h3>
                                    <p className="pre-op-modal__subtitle">{selectedPreOp.type} — {selectedPreOp.patient}</p>
                                </div>
                                <button className="pre-op-modal__close" onClick={() => setSelectedPreOp(null)}>×</button>
                            </div>
                            <div className="pre-op-modal__content">
                                {!isMockMode() && (
                                    <div className="pre-op-suggestions-bar" style={{ marginBottom: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--surface-bg)', borderRadius: 'var(--radius-md)' }}>
                                        {suggestionsLoading && <p className="pre-op-suggestions-loading" style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Loading AI suggestions…</p>}
                                        {suggestionsError && !/^HTTP \d+$/.test(suggestionsError) && (
                                            <p className="pre-op-suggestions-error" style={{ margin: '0 0 8px 0', fontSize: 'var(--text-sm)', color: 'var(--color-error, #c00)' }}>{suggestionsError}</p>
                                        )}
                                        <button
                                            type="button"
                                            className="btn btn--outline"
                                            style={{ fontSize: 'var(--text-sm)' }}
                                            onClick={fetchSuggestions}
                                            disabled={suggestionsLoading}
                                        >
                                            {suggestionsLoading ? 'Loading…' : 'Get AI suggestions'}
                                        </button>
                                    </div>
                                )}
                                {/* Equipment Section */}
                                <div className="pre-op-section">
                                    <h4 className="pre-op-section__title">🛠 Required Equipment</h4>
                                    <div className="pre-op-checklist">
                                        {sessionData.equipment.map((item, idx) => (
                                            <label key={`eq-${idx}`} className={`pre-op-checkbox-item ${item.checked ? 'is-checked' : ''}`}>
                                                <input
                                                    type="checkbox"
                                                    checked={item.checked}
                                                    onChange={() => toggleItem('equipment', idx)}
                                                />
                                                <span className="checkbox-custom"></span>
                                                <span className="item-name">{item.name}</span>
                                            </label>
                                        ))}
                                    </div>
                                    <div className="pre-op-add-item">
                                        <input
                                            type="text"
                                            placeholder="Add equipment..."
                                            value={newItemTexts.equipment}
                                            onChange={(e) => setNewItemTexts({ ...newItemTexts, equipment: e.target.value })}
                                            onKeyDown={(e) => e.key === 'Enter' && addItem('equipment')}
                                        />
                                        <button onClick={() => addItem('equipment')}>Add</button>
                                    </div>
                                </div>

                                {/* Checklist Section */}
                                <div className="pre-op-section">
                                    <h4 className="pre-op-section__title">📋 Pre-Operation Checklist</h4>
                                    <div className="pre-op-checklist">
                                        {sessionData.checklist.map((item, idx) => (
                                            <label key={`ch-${idx}`} className={`pre-op-checkbox-item ${item.checked ? 'is-checked' : ''}`}>
                                                <input
                                                    type="checkbox"
                                                    checked={item.checked}
                                                    onChange={() => toggleItem('checklist', idx)}
                                                />
                                                <span className="checkbox-custom"></span>
                                                <span className="item-name">{item.name}</span>
                                            </label>
                                        ))}
                                    </div>
                                    <div className="pre-op-add-item">
                                        <input
                                            type="text"
                                            placeholder="Add checklist item..."
                                            value={newItemTexts.checklist}
                                            onChange={(e) => setNewItemTexts({ ...newItemTexts, checklist: e.target.value })}
                                            onKeyDown={(e) => e.key === 'Enter' && addItem('checklist')}
                                        />
                                        <button onClick={() => addItem('checklist')}>Add</button>
                                    </div>
                                </div>
                            </div>
                            <div className="pre-op-modal__footer">
                                <button className="btn btn--primary" onClick={() => setSelectedPreOp(null)}>Done</button>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
}
