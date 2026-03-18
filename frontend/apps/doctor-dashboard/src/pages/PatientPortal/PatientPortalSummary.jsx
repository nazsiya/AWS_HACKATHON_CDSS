import { useOutletContext } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { pickTranslated, pickTranslatedList, t } from '../../components/PatientPortal/i18n';
import { resolvePortalPatient } from '../../components/PatientPortal/resolvePortalPatient';
import './PatientPortalPages.css';

function Section({ title, children }) {
    return (
        <div className="patient-portal-section" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="patient-portal-section__head">
                <h2 className="patient-portal-section__title">{title}</h2>
            </div>
            {children}
        </div>
    );
}

export default function PatientPortalSummary() {
    const { user } = useAuth();
    const { language } = useOutletContext() || { language: 'en' };
    const patient = resolvePortalPatient(user);
    const summary = patient?.portal?.aiVisitSummary || {};
    const preOp = patient?.portal?.preOpChecklist || null;

    const available = Boolean(summary?.available);
    const sections = summary?.sections || {};
    const tips = pickTranslatedList(sections?.tips, language);
    const cautions = pickTranslatedList(sections?.cautions, language);

    return (
        <div className="patient-portal-page">
            <h1 className="patient-portal-page__title">{t(language, 'summary_title')}</h1>
            <p className="patient-portal-page__desc">
                <span className="patient-portal-inline-muted">{t(language, 'summary_currentLanguage')}:</span> {String(language || 'en').toUpperCase()}
            </p>

            {!available ? (
                <div className="patient-portal-empty">{t(language, 'summary_notAvailable')}</div>
            ) : (
                <>
                    <Section title={t(language, 'summary_agentIdentity')}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <span aria-hidden="true" style={{ fontSize: '20px' }}>🤖</span>
                            <strong style={{ color: 'var(--text-primary)' }}>{summary?.agentName || 'AI Agent'}</strong>
                        </div>
                    </Section>

                    <Section title={t(language, 'summary_clinicalMeta')}>
                        <div style={{ display: 'grid', gap: '6px', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                            <div><span className="patient-portal-inline-muted">{t(language, 'summary_lastVisitDate')}:</span> {summary?.lastVisitDate || '—'}</div>
                            <div><span className="patient-portal-inline-muted">{t(language, 'summary_treatingPhysician')}:</span> {summary?.treatingPhysician || '—'}</div>
                        </div>
                    </Section>

                    {sections?.abstract ? (
                        <Section title={t(language, 'summary_abstract')}>
                            <div style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)', lineHeight: 1.5 }}>
                                {pickTranslated(sections.abstract, language)}
                            </div>
                        </Section>
                    ) : null}

                    {sections?.reasoning ? (
                        <Section title={t(language, 'summary_reasoning')}>
                            <div style={{ color: 'var(--text-primary)', fontSize: 'var(--text-sm)', lineHeight: 1.5 }}>
                                {pickTranslated(sections.reasoning, language)}
                            </div>
                        </Section>
                    ) : null}

                    {preOp ? (
                        <Section title="Pre-op checklist (demo)">
                            <div style={{ display: 'grid', gap: '6px', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                                <div>
                                    <span className="patient-portal-inline-muted">Planned surgery:</span> {preOp.surgery || '—'}
                                </div>
                                <div>
                                    <span className="patient-portal-inline-muted">Scheduled:</span> {preOp.scheduledDateTime ? new Date(preOp.scheduledDateTime).toLocaleString() : '—'}
                                </div>
                            </div>
                            <div style={{ marginTop: 'var(--space-3)' }}>
                                {(preOp.checklist || []).length === 0 ? (
                                    <div className="patient-portal-empty">No checklist items.</div>
                                ) : (
                                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '10px' }}>
                                        {preOp.checklist.map((item, idx) => (
                                            <li
                                                key={`${item.name}-${idx}`}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '10px',
                                                    padding: '10px 12px',
                                                    border: '1px solid var(--surface-border)',
                                                    borderRadius: 'var(--radius-md)',
                                                    background: 'var(--surface-bg)',
                                                }}
                                            >
                                                <input type="checkbox" checked={!!item.checked} readOnly aria-label={item.name} />
                                                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.name}</span>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                {preOp.disclaimer ? (
                                    <div className="patient-portal-page__hint" style={{ marginTop: 'var(--space-3)' }}>
                                        {preOp.disclaimer}
                                    </div>
                                ) : null}
                            </div>
                        </Section>
                    ) : null}

                    <div className="patient-portal-grid-2">
                        <Section title={t(language, 'summary_tips')}>
                            {tips.length === 0 ? (
                                <div className="patient-portal-empty">{t(language, 'summary_noTips')}</div>
                            ) : (
                                <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>
                                    {tips.map((t, idx) => <li key={idx}>{t}</li>)}
                                </ul>
                            )}
                        </Section>

                        <Section title={t(language, 'summary_cautions')}>
                            {cautions.length === 0 ? (
                                <div className="patient-portal-empty">{t(language, 'summary_noCautions')}</div>
                            ) : (
                                <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--text-primary)', fontSize: 'var(--text-sm)' }}>
                                    {cautions.map((c, idx) => <li key={idx}>{c}</li>)}
                                </ul>
                            )}
                        </Section>
                    </div>
                </>
            )}
        </div>
    );
}

