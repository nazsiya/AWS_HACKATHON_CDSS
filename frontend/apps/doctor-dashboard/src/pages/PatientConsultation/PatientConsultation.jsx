import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useActivity } from '../../context/ActivityContext';
import { isMockMode } from '../../api/config';
import { getPatient, saveConsultation, postAgent, postSummarize } from '../../api/client';
import { patients, consultationHistory } from '../../data/mockData';
import './PatientConsultation.css';

const getInitials = (name) => name.split(' ').map(n => n[0]).join('');

const SUMMARY_LANG_KEY = 'cdss_summary_lang';
const summaryLangLabels = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' };
const summaryLangHeadings = {
    en: 'AI summary & recommendations',
    hi: 'रोगी सारांश और सिफारिशें (AI summary)',
    ta: 'நோயாளி சுருக்கம் (AI summary)',
    te: 'రోగి సారాంశం (AI summary)',
    bn: 'রোগী সারাংশ (AI summary)',
};

const aiResponses = [
    { role: 'assistant', text: "Hello Dr. Sharma, I've pulled up this patient's complete history. Based on the latest vitals and lab results, here's my assessment:", time: '10:01 AM' },
    { role: 'assistant', text: "📊 **Key Findings:**\n• Blood pressure trending upward (130/85 → needs monitoring)\n• HbA1c at 7.8% — above target of 7.0%\n• Current Amlodipine dose was recently increased to 10mg\n\n💡 **Recommendation:** Consider adding a second antihypertensive (e.g., Losartan 25mg) if BP remains elevated at next visit.", time: '10:01 AM' },
    { role: 'user', text: "What about drug interactions with the current medications?", time: '10:02 AM' },
    { role: 'assistant', text: "✅ **Drug Interaction Check:**\n• Metformin 500mg + Amlodipine 10mg — **No significant interactions**\n• If adding Losartan: Metformin + Losartan — **Safe combination**, but monitor renal function (creatinine) every 3 months.\n\n⚠️ **Note:** Avoid combining with NSAIDs as it may reduce antihypertensive efficacy and affect renal function.", time: '10:02 AM' },
];

const suggestions = [
    "Summarize patient history",
    "Check drug interactions",
    "Generate prescription",
    "Suggest lab tests",
    "Pre-op assessment",
];

export default function PatientConsultation() {
    const { patientId } = useParams();
    const navigate = useNavigate();
    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState(() => (isMockMode() ? aiResponses : []));
    const [isTyping, setIsTyping] = useState(false);
    const [patient, setPatient] = useState(null);
    const [history, setHistory] = useState(consultationHistory);
    const [loading, setLoading] = useState(!isMockMode());
    const [error, setError] = useState(null);
    const [consultationStarted, setConsultationStarted] = useState(false);
    const [consultationNotes, setConsultationNotes] = useState('');
    const [savingNotes, setSavingNotes] = useState(false);
    const [consultationStartTime, setConsultationStartTime] = useState(null);
    const [visitId, setVisitId] = useState(null);
    const [surgeryReadinessModalOpen, setSurgeryReadinessModalOpen] = useState(false);
    const [surgeryReadinessAiLoading, setSurgeryReadinessAiLoading] = useState(false);
    const [surgeryReadinessAiReply, setSurgeryReadinessAiReply] = useState('');
    const [surgeryReadinessAiError, setSurgeryReadinessAiError] = useState(null);
    const [chatError, setChatError] = useState(null);
    const [consultationError, setConsultationError] = useState(null);
    const [dbUnavailable, setDbUnavailable] = useState(false);
    const [savedLocallyMessage, setSavedLocallyMessage] = useState(false);
    const [notesSummary, setNotesSummary] = useState('');
    const [notesSummaryLoading, setNotesSummaryLoading] = useState(false);
    const [notesSummaryError, setNotesSummaryError] = useState(null);
    const { user } = useAuth();
    const { logActivity } = useActivity();

    const summaryLang = typeof localStorage !== 'undefined' ? (localStorage.getItem(SUMMARY_LANG_KEY) || 'en') : 'en';

    useEffect(() => {
        if (isMockMode()) {
            setPatient(patients.find(p => p.id === patientId) || null);
            setHistory(consultationHistory);
            return;
        }
        if (!patientId) return;
        let cancelled = false;
        setLoading(true);
        setError(null);
        getPatient(patientId)
            .then((data) => {
                if (cancelled) return;
                setPatient(data);
                const apiHistory = data.consultationHistory || data.consultations || [];
                try {
                    const key = `cdss_local_notes_${patientId}`;
                    const localRaw = localStorage.getItem(key);
                    const localList = localRaw ? JSON.parse(localRaw) : [];
                    const combined = [...apiHistory];
                    const seen = new Set(apiHistory.map(c => c.id));
                    localList.forEach(entry => {
                        if (entry && entry.id && !seen.has(entry.id)) {
                            combined.push(entry);
                            seen.add(entry.id);
                        }
                    });
                    setHistory(combined);
                } catch (_) {
                    setHistory(apiHistory);
                }
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load patient');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [patientId]);

    useEffect(() => {
        if (patientId && patient) logActivity('view_patient', { patientId });
    }, [patientId, patient, logActivity]);

    useEffect(() => {
        if (!savedLocallyMessage) return;
        const t = setTimeout(() => setSavedLocallyMessage(false), 4000);
        return () => clearTimeout(t);
    }, [savedLocallyMessage]);

    // Auto-summarize consultation notes so "AI summary of your notes" updates without the doctor clicking fetch
    const autoSummarizeDebounceRef = useRef(null);
    useEffect(() => {
        const notesText = (consultationNotes || '').trim();
        if (!notesText || notesText.length < 10) {
            if (!notesText) setNotesSummary('');
            return;
        }
        if (autoSummarizeDebounceRef.current) clearTimeout(autoSummarizeDebounceRef.current);
        setNotesSummaryLoading(true);
        setNotesSummaryError(null);
        autoSummarizeDebounceRef.current = setTimeout(() => {
            autoSummarizeDebounceRef.current = null;
            if (isMockMode()) {
                setNotesSummary(`[Mock] Summary: ${notesText.slice(0, 100)}${notesText.length > 100 ? '…' : ''}.`);
                setNotesSummaryLoading(false);
                return;
            }
            postSummarize({ text: notesText })
                .then((data) => {
                    const summary = (data && data.summary) ? String(data.summary).trim() : '';
                    if (summary && !/unavailable|error/i.test(summary)) {
                        setNotesSummary(summary);
                    } else if (summary) {
                        setNotesSummary(summary);
                    }
                })
                .catch(() => {})
                .finally(() => setNotesSummaryLoading(false));
        }, 2500);
        return () => {
            if (autoSummarizeDebounceRef.current) clearTimeout(autoSummarizeDebounceRef.current);
        };
    }, [consultationNotes]);

    const patientResolved = patient || (isMockMode() ? patients.find(p => p.id === patientId) : null);

    if (!patientResolved && !loading) {
        return (
            <div className="page-enter" style={{ textAlign: 'center', padding: '4rem' }}>
                <h2>Patient not found</h2>
                <button className="btn btn--primary" onClick={() => navigate('/patients')} style={{ marginTop: '1rem' }}>
                    ← Back to Patients
                </button>
            </div>
        );
    }

    if (loading && !isMockMode()) {
        return (
            <div className="page-enter" style={{ padding: '4rem', textAlign: 'center' }}>
                <p>Loading patient…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page-enter" style={{ padding: '4rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--color-error, #c00)' }}>{error}</p>
                <button className="btn btn--primary" onClick={() => navigate('/patients')}>← Back to Patients</button>
            </div>
        );
    }

    const vitalStatus = (label, value) => {
        if (label === 'SpO2' && value < 92) return 'critical';
        if (label === 'HR' && (value > 100 || value < 60)) return 'warning';
        if (label === 'Temp' && value > 100) return 'warning';
        return 'normal';
    };

    const vitals = patientResolved.vitals || {};
    const vitalValues = [
        { icon: '💓', label: 'HR', value: vitals.hr, unit: 'bpm' },
        { icon: '🩸', label: 'BP', value: vitals.bp, unit: 'mmHg' },
        { icon: '🫁', label: 'SpO2', value: vitals.spo2, unit: '%' },
        { icon: '🌡️', label: 'Temp', value: vitals.temp, unit: '°F' },
    ];

    const formatTime = (d) => {
        if (!d || !(d instanceof Date)) return 'Now';
        const h = d.getHours(), m = d.getMinutes();
        const am = h < 12 ? 'AM' : 'PM';
        return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${am}`;
    };

    const handleSend = () => {
        if (!message.trim()) return;
        const userMessage = message.trim();
        setMessages(prev => [...prev, { role: 'user', text: userMessage, time: formatTime(new Date()) }]);
        setMessage('');
        setIsTyping(true);
        setChatError(null);
        logActivity('ai_chat_patient', { patientId });

        if (isMockMode()) {
            setTimeout(() => {
                setIsTyping(false);
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    text: "I've analyzed your query. Based on the patient's current condition and medical history, I recommend proceeding with the standard protocol. Would you like me to generate a detailed treatment plan?",
                    time: formatTime(new Date()),
                }]);
            }, 2000);
            return;
        }

        const patientSnapshot = {
            patient: patientResolved ? {
                id: patientResolved.id,
                name: patientResolved.name,
                age: patientResolved.age,
                gender: patientResolved.gender,
                bloodGroup: patientResolved.bloodGroup,
                ward: patientResolved.ward,
                severity: patientResolved.severity,
                vitals: patientResolved.vitals,
                conditions: patientResolved.conditions,
                medicationsCount: history.reduce((n, c) => n + (c.prescriptions || []).length, 0),
                surgeryReadiness: patientResolved.surgeryReadiness,
                nextAppointment: patientResolved.nextAppointment || null,
                nextAppointmentDetails: patientResolved.nextAppointmentDetails || null,
            } : null,
            recentConsultations: (history || []).slice(-5).map((c) => ({
                date: c.date,
                doctor: c.doctor,
                notes: c.notes,
                aiSummary: c.aiSummary,
                prescriptions: (c.prescriptions || []).map((rx) => ({
                    medication: rx.medication,
                    dosage: rx.dosage,
                    frequency: rx.frequency,
                    duration: rx.duration,
                })),
            })),
            doctorNotesDraft: (consultationNotes || '').slice(0, 2000),
        };

        postAgent({
            message: userMessage,
            patient_id: patientId,
            history: messages.map(m => ({ role: m.role, text: m.text })),
            context: { patient_snapshot: patientSnapshot },
        })
            .then((data) => {
                const inner = data?.data;
                const reply = (inner && inner.reply) ?? data.reply ?? data.message ?? data.summary ?? (typeof data === 'string' ? data : 'Unable to generate response.');
                const disclaimer = inner?.safety_disclaimer ?? data.safety_disclaimer;
                setMessages(prev => [...prev, { role: 'assistant', text: reply, time: formatTime(new Date()), ...(disclaimer ? { safety_disclaimer: disclaimer } : {}) }]);
            })
            .catch((err) => {
                const errMsg = err?.message || 'Failed to get AI response';
                setChatError(errMsg);
                setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${errMsg}`, time: formatTime(new Date()) }]);
            })
            .finally(() => setIsTyping(false));
    };

    const handleStartConsultation = () => {
        // Works immediately: no API required. Shows doctor notes + AI summary from notes.
        logActivity('start_consultation', { patientId });
        setConsultationError(null);
        setDbUnavailable(false);
        setConsultationStartTime(new Date());
        setVisitId('local-' + Date.now());
        setConsultationStarted(true);
    };

    const handleSaveConsultationNotes = () => {
        setSavingNotes(true);
        logActivity('save_consultation', { patientId, detail: 'Consultation notes saved' });
        const notesText = (consultationNotes || '').trim();

        if (isMockMode()) {
            const mockSummary = notesSummary || `[Mock] Summary of notes: ${notesText.slice(0, 60)}${notesText.length > 60 ? '…' : ''}.`;
            setTimeout(() => {
                setHistory(prev => [...prev, {
                    id: `consult-${Date.now()}`,
                    date: new Date().toISOString().slice(0, 10),
                    doctor: user?.name || 'Current Doctor',
                    notes: consultationNotes || '—',
                    aiSummary: mockSummary,
                    prescriptions: [],
                }]);
                setConsultationNotes('');
                setSavingNotes(false);
            }, 500);
            return;
        }

        const doSave = (summaryToUse) => {
            const summaryToSave = (summaryToUse || '').trim() || '—';
            const payload = {
                notes: consultationNotes,
                ai_summary: summaryToSave,
                summary: summaryToSave,
                ...(visitId != null && visitId !== '' && !String(visitId).startsWith('local-') && { visit_id: visitId }),
            };
            const addToHistoryLocal = () => {
                const entry = {
                    id: `consult-${Date.now()}`,
                    date: new Date().toISOString().slice(0, 10),
                    doctor: user?.name,
                    notes: consultationNotes,
                    aiSummary: summaryToSave || '—',
                    prescriptions: [],
                };
                setHistory(prev => [...prev, entry]);
                setConsultationNotes('');
                setSavedLocallyMessage(true);
                try {
                    const key = `cdss_local_notes_${patientId}`;
                    const existing = JSON.parse(localStorage.getItem(key) || '[]');
                    existing.push(entry);
                    localStorage.setItem(key, JSON.stringify(existing.slice(-50)));
                } catch (_) { /* ignore */ }
            };
            if (dbUnavailable || (visitId && String(visitId).startsWith('local-'))) {
                addToHistoryLocal();
                setSavingNotes(false);
                return;
            }
            saveConsultation(patientId, payload)
                .then(() => {
                    setHistory(prev => [...prev, {
                        id: `consult-${Date.now()}`,
                        date: new Date().toISOString().slice(0, 10),
                        doctor: user?.name,
                        notes: consultationNotes,
                        aiSummary: summaryToSave,
                        prescriptions: [],
                    }]);
                    setConsultationNotes('');
                })
                .catch(() => {
                    addToHistoryLocal();
                })
                .finally(() => setSavingNotes(false));
        };

        // Use only doctor notes for AI summary (no conversation). Prefer existing notesSummary from "Get AI summary from notes".
        if (notesSummary && notesSummary.trim()) {
            doSave(notesSummary);
            return;
        }
        if (notesText) {
            postSummarize({ text: notesText })
                .then((data) => {
                    const summary = (data && data.summary) ? String(data.summary).trim() : '';
                    const useSummary = summary && !/unavailable|error/i.test(summary) ? summary : '—';
                    setNotesSummary(useSummary);
                    doSave(useSummary);
                })
                .catch(() => doSave('—'));
        } else {
            doSave('—');
        }
    };

    const handleSummarizeNotes = () => {
        const notesText = (consultationNotes || '').trim();
        if (!notesText) return;
        setNotesSummaryError(null);
        setNotesSummaryLoading(true);
        if (isMockMode()) {
            setTimeout(() => {
                setNotesSummary(`[Mock] Summary of your notes: ${notesText.slice(0, 80)}${notesText.length > 80 ? '…' : ''}. Key points extracted for clinical record.`);
                setNotesSummaryLoading(false);
            }, 800);
            return;
        }
        postSummarize({ text: notesText })
            .then((data) => {
                const summary = (data && data.summary) ? String(data.summary).trim() : '';
                const isUnavailable = !summary || /unavailable|error/i.test(summary);
                if (summary && !isUnavailable) {
                    setNotesSummary(summary);
                } else if (summary) {
                    // Backend may return fallback text when AI is not configured; still show it
                    setNotesSummary(summary);
                } else {
                    setNotesSummary(
                        'AI summarization is not available. Ensure the API is running, VITE_API_URL is set, and Bedrock is configured (see docs/BEDROCK_LOCAL_SETUP.md).'
                    );
                }
            })
            .catch((err) => {
                setNotesSummaryError(err?.message || 'Failed to summarize notes');
            })
            .finally(() => setNotesSummaryLoading(false));
    };

    const handleGetSurgeryReadinessSummary = () => {
        setSurgeryReadinessAiError(null);
        setSurgeryReadinessAiLoading(true);
        setSurgeryReadinessAiReply('');
        const message = "Provide a surgery readiness and pre-op assessment summary for this patient. Include risk factors, pre-op checklist considerations, and any recommendations.";
        if (isMockMode()) {
            setTimeout(() => {
                setSurgeryReadinessAiReply("Based on the patient's profile: Hypertension is a key risk factor. Recommend BP control to target before procedure. Pre-op checklist: confirm medications (e.g. Amlodipine), fasting instructions, and consent. Consider cardiology clearance if BP remains elevated.");
                setSurgeryReadinessAiLoading(false);
            }, 1500);
            return;
        }
        postAgent({ message, patient_id: patientId })
            .then((data) => {
                const inner = data?.data;
                const reply = (inner && inner.reply) ?? data.reply ?? data.message ?? data.summary ?? (typeof data === 'string' ? data : '');
                setSurgeryReadinessAiReply(reply);
            })
            .catch((err) => setSurgeryReadinessAiError(err?.message || 'Failed to get AI summary'))
            .finally(() => setSurgeryReadinessAiLoading(false));
    };

    const clinicalRiskScore = (() => {
        const s = (patientResolved?.severity || '').toLowerCase();
        if (s === 'critical') return 8;
        if (s === 'high') return 6;
        if (s === 'moderate') return 4;
        if (s === 'low') return 2;
        return 5;
    })();

    return (
        <div className="page-enter">
            <a className="back-link" onClick={() => navigate(-1)}>← Back</a>

            <div className="patient-view">
                {/* Left: Patient Details */}
                <div className="patient-details">
                    {/* Patient Header */}
                    <div className="patient-header animate-in">
                        <div className="patient-header__row">
                            <div className={`patient-header__avatar patient-header__avatar--${patientResolved.gender.toLowerCase()}`}>
                                {getInitials(patientResolved.name)}
                            </div>
                            <div className="patient-header__info">
                                <div className="patient-header__name">{patientResolved.name}</div>
                                <div className="patient-header__meta">
                                    <span className="patient-header__meta-item patient-header__meta-item--id" title="Unique identifier for all medical interactions">🆔 Patient ID: {patientResolved.id}</span>
                                    <span className="patient-header__meta-item">🎂 {patientResolved.age} years</span>
                                    <span className="patient-header__meta-item">🩸 {patientResolved.bloodGroup}</span>
                                    <span className="patient-header__meta-item">🏥 {patientResolved.ward}</span>
                                </div>
                                <div className="patient-header__key-indicators">
                                    <span className="patient-header__ki">Allergies: None documented</span>
                                    <span className="patient-header__ki">Conditions: {(patientResolved.conditions || []).length}</span>
                                    <span className="patient-header__ki">Medications: {history.reduce((n, c) => n + (c.prescriptions || []).length, 0)}</span>
                                </div>
                                <div className="patient-header__risk-meter">
                                    <span className="patient-header__risk-label">Risk</span>
                                    <div className="patient-header__risk-bar">
                                        <div className="patient-header__risk-fill" style={{ width: `${clinicalRiskScore * 10}%` }} />
                                    </div>
                                    <span className="patient-header__risk-value">{clinicalRiskScore}/10</span>
                                </div>
                                <div className="patient-header__conditions">
                                    {(patientResolved.conditions || []).map((cond, i) => (
                                        <span key={i} className="condition-tag">{cond}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="patient-header__actions">
                            {!consultationStarted ? (
                                <button className="btn btn--primary" onClick={handleStartConsultation}>
                                    ▶ Start consultation
                                </button>
                            ) : (
                                <span className="consultation-badge">Consultation active</span>
                            )}
                            <button className="btn btn--primary">📝 New Prescription</button>
                            <button className="btn btn--outline" onClick={() => navigate('/surgery', { state: { patientId, patientName: patientResolved.name } })}>
                                🔪 Surgery required
                            </button>
                            <button className="btn btn--outline" onClick={() => setSurgeryReadinessModalOpen(true)}>
                                🩺 Surgery Readiness (AI Agent)
                            </button>
                            <button className="btn btn--outline">📋 Refer</button>
                        </div>
                        {consultationError && (
                            <p className="patient-header__error" role="alert" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-error, #c00)' }}>
                                {consultationError}
                            </p>
                        )}
                    </div>

                    {/* Surgery Readiness Modal (AI Agent) */}
                    {surgeryReadinessModalOpen && (
                        <div className="surgery-readiness-modal-overlay" onClick={() => setSurgeryReadinessModalOpen(false)}>
                            <div className="surgery-readiness-modal" onClick={e => e.stopPropagation()}>
                                <div className="surgery-readiness-modal__header">
                                    <h3>🩺 Surgery Readiness (AI Agent)</h3>
                                    <button type="button" className="surgery-readiness-modal__close" onClick={() => setSurgeryReadinessModalOpen(false)}>×</button>
                                </div>
                                <div className="surgery-readiness-modal__body">
                                    <div className="surgery-readiness-modal__row">
                                        <span>Risk Score & Safety Gauge</span>
                                        <span>{clinicalRiskScore}/10 — {(clinicalRiskScore <= 3 ? 'Low' : clinicalRiskScore <= 6 ? 'Moderate' : 'High')} risk</span>
                                    </div>
                                    <div className="surgery-readiness-modal__row">
                                        <span>Estimated Procedure Duration</span>
                                        <span>— (varies by procedure)</span>
                                    </div>
                                    <div className="surgery-readiness-modal__row">
                                        <span>Required Specialists & Instruments</span>
                                        <span>Per procedure type; see Surgery Planning.</span>
                                    </div>
                                    <div className="surgery-readiness-modal__row">
                                        <span>Pre-Op Checklist Compliance</span>
                                        <span className={`surgery-readiness-modal__status surgery-readiness-modal__status--${(patientResolved.surgeryReadiness?.preOpStatus || 'pending')}`}>
                                            {(patientResolved.surgeryReadiness?.preOpStatus || 'Pending').replace(/_/g, ' ')}
                                        </span>
                                    </div>
                                    <div className="surgery-readiness-modal__row">
                                        <span>Risk Flags</span>
                                        <ul>
                                            {(patientResolved.surgeryReadiness?.riskFactors || patientResolved.conditions || []).slice(0, 5).map((r, i) => (
                                                <li key={i}>{typeof r === 'string' ? r : r}</li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="surgery-readiness-modal__ai-section">
                                        <h4 className="surgery-readiness-modal__ai-title">Start conversation — AI summary</h4>
                                        <p className="surgery-readiness-modal__ai-desc">Get a surgery readiness and pre-op assessment from the AI agent.</p>
                                        <button
                                            type="button"
                                            className="btn btn--primary"
                                            onClick={handleGetSurgeryReadinessSummary}
                                            disabled={surgeryReadinessAiLoading}
                                        >
                                            {surgeryReadinessAiLoading ? 'Getting summary…' : 'Get AI summary'}
                                        </button>
                                        {surgeryReadinessAiError && (
                                            <p className="surgery-readiness-modal__ai-error">{surgeryReadinessAiError}</p>
                                        )}
                                        {surgeryReadinessAiReply && (
                                            <div className="surgery-readiness-modal__ai-reply">
                                                <strong>AI summary</strong>
                                                <div className="surgery-readiness-modal__ai-reply-text">{surgeryReadinessAiReply}</div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {consultationStarted && (
                        <div className="ai-summary-block animate-in">
                            <div className="consultation-notes-form">
                                <label className="consultation-notes-label">Consultation notes (doctor notes only)</label>
                                {dbUnavailable && (
                                    <p className="consultation-notes-offline" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-warning, #b8860b)', marginBottom: 'var(--space-2)' }}>
                                        Database unavailable — notes are saved locally and will appear in the timeline below.
                                    </p>
                                )}
                                <textarea
                                    className="consultation-notes-input"
                                    placeholder="Add your notes here..."
                                    value={consultationNotes}
                                    onChange={e => setConsultationNotes(e.target.value)}
                                    rows={4}
                                />
                                <button type="button" className="btn btn--primary" onClick={handleSaveConsultationNotes} disabled={savingNotes}>
                                    {savingNotes ? 'Saving…' : 'Save consultation notes'}
                                </button>
                                {savedLocallyMessage && (
                                    <p className="consultation-notes-saved-local" role="status" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-success, #0a0)' }}>
                                        Notes saved locally. They will sync when the database is available.
                                    </p>
                                )}
                                <div style={{ marginTop: 'var(--space-4)' }}>
                                    <button
                                        type="button"
                                        className="btn btn--outline"
                                        onClick={handleSummarizeNotes}
                                        disabled={notesSummaryLoading || !(consultationNotes || '').trim()}
                                    >
                                        {notesSummaryLoading ? 'Summarizing…' : '✨ Get AI summary from notes'}
                                    </button>
                                    {notesSummaryError && (
                                        <p className="consultation-notes-offline" role="alert" style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-error, #c00)' }}>
                                            {notesSummaryError}
                                        </p>
                                    )}
                                </div>
                            </div>
                            {/* AI summarised output — below the notes, from doctor notes only */}
                            <div className="ai-summary-block ai-summary-block--notes" style={{ marginTop: 'var(--space-3)' }}>
                                <div className="card-header">
                                    <span className="card-header__title">📄 AI summary of your notes</span>
                                </div>
                                <p className="ai-summary-block__clinical-note">Summary appears here automatically as you type. You can also click &quot;Get AI summary from notes&quot; to refresh.</p>
                                <div className="ai-summary-block__content">
                                    {notesSummaryLoading && (
                                        <div className="ai-summary-placeholder">
                                            <p>Analyzing your notes…</p>
                                            <div className="loading-dots"><span>.</span><span>.</span><span>.</span></div>
                                        </div>
                                    )}
                                    {!notesSummaryLoading && notesSummary && (
                                        <div>{notesSummary}</div>
                                    )}
                                    {!notesSummaryLoading && !notesSummary && (
                                        <p className="ai-summary-placeholder" style={{ color: 'var(--color-text-muted, #666)' }}>
                                            Type your notes above; the summary will appear here automatically after a short pause.
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Surgery readiness (Req 2.4) */}
                    {(patientResolved.surgeryReadiness || (patientResolved.conditions && patientResolved.conditions.length > 0)) && (
                        <div className="surgery-readiness-block animate-in">
                            <div className="card-header">
                                <span className="card-header__title">🩺 Surgery readiness</span>
                            </div>
                            <div className="surgery-readiness__content">
                                <div className="surgery-readiness__row">
                                    <span className="surgery-readiness__label">Pre-op status</span>
                                    <span className={`surgery-readiness__status surgery-readiness__status--${(patientResolved.surgeryReadiness?.preOpStatus || 'not_assessed').replace('-', '_')}`}>
                                        {(patientResolved.surgeryReadiness?.preOpStatus || 'Not assessed').replace(/_/g, ' ')}
                                    </span>
                                </div>
                                {(patientResolved.surgeryReadiness?.lastAssessed) && (
                                    <div className="surgery-readiness__row">
                                        <span className="surgery-readiness__label">Last assessed</span>
                                        <span className="surgery-readiness__value">{patientResolved.surgeryReadiness.lastAssessed}</span>
                                    </div>
                                )}
                                <div className="surgery-readiness__row">
                                    <span className="surgery-readiness__label">Risk factors</span>
                                    <ul className="surgery-readiness__risks">
                                        {(patientResolved.surgeryReadiness?.riskFactors || []).length > 0
                                            ? patientResolved.surgeryReadiness.riskFactors.map((r, i) => <li key={i}>{r}</li>)
                                            : (patientResolved.conditions || []).map((c, i) => <li key={i}>{c}</li>)}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Vitals Grid */}
                    <div className="vitals-grid">
                        {vitalValues.map((vital, i) => {
                            const valueNum = typeof vital.value === 'string' ? parseInt(vital.value, 10) : vital.value;
                            const status = vitalStatus(vital.label, valueNum);
                            return (
                                <div key={i} className={`vital-card animate-in animate-in-delay-${i + 1} ${status === 'critical' ? 'vital-card--critical' : ''}`}>
                                    <div className="vital-card__icon">{vital.icon}</div>
                                    <div className="vital-card__value">{vital.value}</div>
                                    <div className="vital-card__label">{vital.label} ({vital.unit})</div>
                                    <div className={`vital-card__status vital-card__status--${status}`}>
                                        {status === 'normal' ? '● Normal' : status === 'warning' ? '● Elevated' : '● Critical'}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Consultation Timeline — chronological medical history (Req 2.2, 2.3) */}
                    <div className="timeline animate-in animate-in-delay-3">
                        <div className="card-header">
                            <span className="card-header__title">📋 Chronological medical history</span>
                        </div>
                        <p className="timeline__desc">Visits with timestamps and treating physician. Complete historical records of treatments, prescriptions, and outcomes.</p>
                        <div className="timeline__list">
                            {[...history]
                                .sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
                                .map((consult, i) => (
                                <div key={consult.id} className={`timeline-item animate-in animate-in-delay-${i + 2}`}>
                                    <div className="timeline-item__dot">📝</div>
                                    <div className="timeline-item__content">
                                        <div className="timeline-item__header">
                                            <span className="timeline-item__date">{consult.date}</span>
                                            <span className="timeline-item__doctor">{consult.doctor}</span>
                                        </div>
                                        <div className="timeline-item__notes">{consult.notes}</div>
                                        <div className="timeline-item__ai-summary">
                                            <div className="timeline-item__ai-label">🤖 AI Summary</div>
                                            {consult.aiSummary}
                                        </div>
                                        <div className="prescription-list">
                                            {(consult.prescriptions || []).map((rx, j) => (
                                                <div key={j} className="prescription-item">
                                                    <span className="prescription-item__name">💊 {rx.medication}</span>
                                                    <span className="prescription-item__dosage">{rx.dosage} · {rx.frequency} · {rx.duration}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right: AI Chat Panel — AI Assistant for this patient */}
                {consultationStarted && (
                <div className="ai-panel animate-in animate-in-delay-2">
                    <div className="ai-panel__header">
                        <div className="ai-panel__indicator" />
                        <span className="ai-panel__title">AI Assistant</span>
                        <span className="ai-panel__subtitle">Amazon Nova Lite</span>
                    </div>

                    <div className="ai-panel__messages">
                        {messages.length === 0 && !isMockMode() && (
                            <div className="ai-panel__empty">
                                Ask about this patient to get AI recommendations. Try &quot;Summarize patient history&quot; or &quot;Pre-op assessment&quot;.
                            </div>
                        )}
                        {messages.map((msg, i) => (
                            <div key={i} className={`ai-message ai-message--${msg.role}`}>
                                <div className="ai-message__bubble">{msg.text}</div>
                                {msg.safety_disclaimer && (
                                    <div className="ai-message__disclaimer" role="note">{msg.safety_disclaimer}</div>
                                )}
                                <div className="ai-message__time">{msg.time}</div>
                            </div>
                        ))}
                        {isTyping && (
                            <div className="ai-typing">
                                <div className="ai-typing__dot" />
                                <div className="ai-typing__dot" />
                                <div className="ai-typing__dot" />
                            </div>
                        )}
                    </div>

                    <div className="ai-panel__suggestions">
                        {suggestions.map((s, i) => (
                            <button key={i} className="ai-suggestion" onClick={() => { setMessage(s); }}>
                                {s}
                            </button>
                        ))}
                    </div>
                    {chatError && (
                        <p className="ai-panel__error" role="alert">{chatError}</p>
                    )}
                    <div className="ai-panel__input">
                        <input
                            type="text"
                            placeholder="Ask AI about this patient..."
                            value={message}
                            onChange={e => setMessage(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSend()}
                        />
                        <button className="ai-panel__send-btn" onClick={handleSend}>↑</button>
                    </div>
                </div>
                )}
            </div>
        </div>
    );
}
