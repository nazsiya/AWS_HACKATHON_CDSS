import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { isMockMode } from '../../api/config';
import { getSurgery } from '../../api/client';
import { connectWs, disconnectWs, subscribeSurgery, addWsListener, isWsEnabled } from '../../api/websocket';
import { surgeries, patients } from '../../data/mockData';
import './SurgeryPlanning.css';

export default function SurgeryPlanning() {
    const { surgeryId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const [surgery, setSurgery] = useState(null);
    const [patient, setPatient] = useState(null);
    const [loading, setLoading] = useState(!isMockMode());
    const [error, setError] = useState(null);
    const [checklist, setChecklist] = useState([
        { id: 1, text: 'Confirm patient identity, site, and procedure', completed: false },
        { id: 2, text: 'Marking of surgical site complete', completed: false },
        { id: 3, text: 'Anesthesia safety check complete', completed: false },
        { id: 4, text: 'Pulse oximeter on patient and functioning', completed: false },
        { id: 5, text: 'Antibiotic prophylaxis administered', completed: false },
        { id: 6, text: 'Confirmation of sterility indicators', completed: false },
    ]);
    const [liveEvents, setLiveEvents] = useState([]);
    const [wsConnected, setWsConnected] = useState(false);
    const [otSlots, setOtSlots] = useState([]);
    const [selectedSlot, setSelectedSlot] = useState(null);
    const [booked, setBooked] = useState(false);
    const [procedureType, setProcedureType] = useState('General');
    const { user } = useAuth();

    const isNewSurgery = surgeryId === 'new';
    const newPatientName = location.state?.patientName || 'Patient';
    const newPatientId = location.state?.patientId;

    // Mock OT availability for "new" surgery
    useEffect(() => {
        if (!isNewSurgery) return;
        setOtSlots([
            { id: 'slot-1', ot: 'OT Room 1 (Main)', date: '2026-03-05', time: '09:00', available: true },
            { id: 'slot-2', ot: 'OT Room 2 (Minor)', date: '2026-03-05', time: '11:00', available: true },
            { id: 'slot-3', ot: 'Cardiac OT', date: '2026-03-06', time: '10:00', available: true },
            { id: 'slot-4', ot: 'OT Room 1 (Main)', date: '2026-03-06', time: '14:00', available: false },
        ]);
    }, [isNewSurgery]);

    useEffect(() => {
        if (isMockMode()) {
            if (isNewSurgery) {
                setLoading(false);
                return;
            }
            const s = surgeries.find(item => item.id === surgeryId);
            if (s) {
                setSurgery(s);
                setPatient(patients.find(item => item.name === s.patient) || null);
            }
            return;
        }
        if (!surgeryId || isNewSurgery) return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        getSurgery(surgeryId)
            .then((data) => {
                if (cancelled) return;
                setSurgery(data);
                setPatient(data.patient ? { ...data.patient } : null);
                if (Array.isArray(data.checklist)) setChecklist(data.checklist);
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load surgery');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [surgeryId]);

    useEffect(() => {
        if (!isWsEnabled() || !surgeryId) return;
        connectWs({
            doctorId: user?.id,
            onOpen: () => {
                setWsConnected(true);
                subscribeSurgery(surgeryId);
            },
            onClose: () => setWsConnected(false),
            reconnect: true,
        });
        const unsub = addWsListener((data) => {
            if (data.checklist_item_id != null && data.completed != null) {
                setChecklist((prev) => prev.map((item) =>
                    item.id === data.checklist_item_id ? { ...item, completed: !!data.completed } : item
                ));
            }
            setLiveEvents((prev) => [{ ...data, at: new Date().toISOString() }, ...prev.slice(0, 19)]);
        });
        return () => {
            unsub();
            disconnectWs();
            setWsConnected(false);
        };
    }, [surgeryId, user?.id]);

    if (isNewSurgery) {
        return (
            <div className="surgery-planning page-enter">
                <header className="planning-header">
                    <button className="back-btn" onClick={() => navigate('/surgery')}>←</button>
                    <h1 className="planning-title">New surgery: {newPatientName}</h1>
                </header>
                <div className="patient-summary-card animate-in">
                    <div className="patient-avatar--large">{newPatientName.split(' ').map(n => n[0]).join('')}</div>
                    <div className="patient-info">
                        <span className="patient-info__name">{newPatientName}</span>
                        <span className="patient-info__meta">Patient ID: {newPatientId || '—'}</span>
                    </div>
                </div>
                <div className="planning-grid">
                    <div className="planning-section animate-in animate-in-delay-1">
                        <h2 className="section-title">Procedure type</h2>
                        <div className="resources-card">
                            <div className="resource-input-group">
                                <label className="resource-label">Type</label>
                                <select className="resource-select" value={procedureType} onChange={(e) => setProcedureType(e.target.value)}>
                                    <option>General</option>
                                    <option>Cardiac</option>
                                    <option>Orthopedic</option>
                                    <option>Laparoscopy</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div className="planning-section animate-in animate-in-delay-2">
                        <h2 className="section-title">OT availability</h2>
                        <div className="resources-card">
                            {otSlots.map((slot) => (
                                <div
                                    key={slot.id}
                                    className={`ot-slot-row ${selectedSlot?.id === slot.id ? 'ot-slot-row--selected' : ''} ${!slot.available ? 'ot-slot-row--unavailable' : ''}`}
                                    style={{ padding: 'var(--space-2)', marginBottom: 'var(--space-2)', borderRadius: 'var(--radius-md)', border: '1px solid var(--surface-border)', cursor: slot.available ? 'pointer' : 'default' }}
                                    onClick={() => slot.available && setSelectedSlot(slot)}
                                >
                                    <strong>{slot.ot}</strong> — {slot.date} {slot.time}
                                    {!slot.available && <span style={{ marginLeft: 'var(--space-2)', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>Booked</span>}
                                </div>
                            ))}
                        </div>
                        <button
                            className="submit-btn animate-in animate-in-delay-3"
                            disabled={!selectedSlot || booked}
                            onClick={() => { setBooked(true); setTimeout(() => navigate('/surgery'), 1500); }}
                        >
                            {booked ? 'Booked ✓' : 'Book slot'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!surgery && !loading) return <div className="page-enter" style={{ padding: '2rem' }}>Surgery not found.</div>;
    if (loading && !isMockMode()) return <div className="page-enter" style={{ padding: '2rem', textAlign: 'center' }}>Loading surgery…</div>;
    if (error) return <div className="page-enter" style={{ padding: '2rem', textAlign: 'center' }}><p style={{ color: 'var(--color-error, #c00)' }}>{error}</p><button className="btn btn--primary" onClick={() => navigate('/surgery')}>← Back</button></div>;

    const toggleCheck = (id) => {
        setChecklist(checklist.map(item =>
            item.id === id ? { ...item, completed: !item.completed } : item
        ));
    };

    return (
        <div className="surgery-planning page-enter">
            <header className="planning-header">
                <button className="back-btn" onClick={() => navigate('/surgery')}>←</button>
                <h1 className="planning-title">Surgery Planning: {surgery.type}</h1>
            </header>

            {/* Patient Summary Banner */}
            <div className="patient-summary-card animate-in">
                <div className="patient-avatar--large">{(typeof surgery.patient === 'string' ? surgery.patient : surgery.patient?.name || '?').split(' ').map(n => n[0]).join('')}</div>
                <div className="patient-info">
                    <span className="patient-info__name">{typeof surgery.patient === 'string' ? surgery.patient : surgery.patient?.name || '—'}</span>
                    <span className="patient-info__meta">
                        ID: PT-{surgeryId.split('-')[1]} • 45y • Male • {surgery.type}
                    </span>
                    <div className="risk-tags" style={{ marginTop: '8px' }}>
                        {patient?.conditions?.map((c, i) => (
                            <span key={i} className={`risk-tag ${c.toLowerCase().includes('diabetes') ? 'risk-tag--high' : 'risk-tag--moderate'}`}>
                                {c}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            <div className="planning-grid">
                {/* Left Column: Surgery blueprint (Req 3) + AI Checklist */}
                <div className="planning-section animate-in animate-in-delay-1">
                    <h2 className="section-title">📋 Surgery requirement blueprint</h2>
                    <div className="blueprint-card">
                        <div className="blueprint-row">
                            <span className="blueprint-label">Type / classification</span>
                            <span className="blueprint-value">{surgery.type}</span>
                        </div>
                        <div className="blueprint-row">
                            <span className="blueprint-label">Complexity</span>
                            <span className="blueprint-value">{surgery.complexity || 'Moderate'}</span>
                        </div>
                        <div className="blueprint-row">
                            <span className="blueprint-label">Estimated duration</span>
                            <span className="blueprint-value">{surgery.estimatedDuration || '90 min'} (with buffer)</span>
                        </div>
                        <div className="blueprint-row">
                            <span className="blueprint-label">Required instruments / tools</span>
                            <ul className="blueprint-list">
                                {(surgery.requiredInstruments || ['Standard surgical set', 'Electrocautery', 'Suction', 'Suture kit']).map((inst, i) => (
                                    <li key={i}>{inst}</li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <h2 className="section-title" style={{ marginTop: 'var(--space-4)' }}>🤖 Clinical guardrails & pre-op checklist</h2>
                    {isWsEnabled() && (
                        <span className={`ws-indicator ${wsConnected ? 'ws-indicator--live' : ''}`} title={wsConnected ? 'Live updates on' : 'Connecting…'}>
                            {wsConnected ? '● Live' : '○ Offline'}
                        </span>
                    )}
                    <div className="checklist-card">
                        {checklist.map((item, i) => (
                            <div
                                key={item.id}
                                className={`ai-checklist-item ${item.completed ? 'checked' : ''}`}
                                onClick={() => toggleCheck(item.id)}
                            >
                                <div className="ai-checklist-item__checkbox"></div>
                                <span className="ai-checklist-item__text">{item.text}</span>
                            </div>
                        ))}
                    </div>
                    {liveEvents.length > 0 && (
                        <div className="live-events">
                            <h3 className="live-events__title">Real-time events</h3>
                            <ul className="live-events__list">
                                {liveEvents.slice(0, 5).map((ev, i) => (
                                    <li key={i} className="live-events__item">
                                        <span className="live-events__time">{ev.at ? new Date(ev.at).toLocaleTimeString() : ''}</span>
                                        <span>{ev.type || ev.message || JSON.stringify(ev)}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                {/* Right Column: Resources & Risk */}
                <div className="planning-section animate-in animate-in-delay-2">
                    <h2 className="section-title">📦 Resource Allocation</h2>
                    <div className="resources-card">
                        <div className="resource-input-group">
                            <label className="resource-label">Operation Theater</label>
                            <select className="resource-select" defaultValue={surgery.ot}>
                                <option>OT Room 1 (Main)</option>
                                <option>OT Room 2 (Minor)</option>
                                <option>Cardiac OT</option>
                                <option>Orthopedic OT</option>
                            </select>
                        </div>
                        <div className="resource-input-group">
                            <label className="resource-label">Surgical Staff Team</label>
                            <select className="resource-select" defaultValue="Team Beta">
                                <option>Team Alpha (Cardiology)</option>
                                <option>Team Beta (Orthopedics)</option>
                                <option>Team Gamma (General)</option>
                            </select>
                        </div>
                        <div className="resource-input-group">
                            <label className="resource-label">Special Equipment</label>
                            <select className="resource-select" defaultValue="C-Arm">
                                <option>None</option>
                                <option>C-Arm Fluoroscopy</option>
                                <option>Surgical Robot (Da Vinci)</option>
                                <option>Laser Lithotripsy</option>
                            </select>
                        </div>
                    </div>

                    <h2 className="section-title" style={{ marginTop: 'var(--space-2)' }}>⚠️ AI Risk Advice</h2>
                    <div className="risk-card">
                        <div className="ai-advice">
                            <strong>Clinical Note:</strong> Patient ID {surgeryId} has Type 2 Diabetes.
                            Ensure blood glucose levels are stabilized below 180 mg/dL prior to incision.
                            Prophylactic antibiotics should be adjusted for renal clearance if necessary.
                        </div>
                    </div>

                    <h2 className="section-title" style={{ marginTop: 'var(--space-2)' }}>📌 Procedural support & complication alerts</h2>
                    <div className="risk-card">
                        <div className="ai-advice">
                            Step-by-step guidance and instrument prompts are available during the procedure (live when WebSocket connected).
                            Potential complications for this case: bleeding risk, infection — ensure sterile technique and haemostasis.
                        </div>
                    </div>
                </div>
            </div>

            <button className="submit-btn animate-in animate-in-delay-3" onClick={() => navigate('/surgery')}>
                Finalize Surgical Plan
            </button>
        </div>
    );
}
