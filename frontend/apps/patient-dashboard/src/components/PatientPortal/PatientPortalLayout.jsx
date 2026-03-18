import { useEffect, useMemo, useState } from 'react';
import { NavLink, useNavigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { patients } from '../../data/mockData';
import { t } from './i18n';
import '../Sidebar/Sidebar.css';
import './PatientPortalLayout.css';

const LANG_OPTIONS = [
    { id: 'en', label: 'EN' },
    { id: 'hi', label: 'हिन्' },
    { id: 'ta', label: 'த' },
];

export default function PatientPortalLayout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [navCollapsed, setNavCollapsed] = useState(false);
    const patient = useMemo(() => patients.find((p) => p.id === user?.id) ||
        patients.find((p) => (p.email || '').toLowerCase() === (user?.email || '').toLowerCase()) ||
        patients[0] || null, [user?.id, user?.email]);

    const storageKey = 'cdss_patient_portal_language';
    const [language, setLanguage] = useState('en');

    const patientNavItems = useMemo(() => ([
        { path: '/', end: true, icon: '🏠', label: t(language, 'nav_dashboard') },
        { path: '/summary', end: false, icon: '🧠', label: t(language, 'nav_summary') },
        { path: '/medication-tracker', end: false, icon: '💊', label: t(language, 'nav_meds') },
        { path: '/appointments', end: false, icon: '📅', label: t(language, 'nav_appts') },
    ]), [language]);

    useEffect(() => {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            setLanguage(saved);
            return;
        }
        const preferred = patient?.portal?.preferredLanguage;
        if (preferred) setLanguage(preferred);
    }, [patient]);

    const handleLanguageChange = (langId) => {
        setLanguage(langId);
        localStorage.setItem(storageKey, langId);
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="patient-portal-layout">
            <aside className={`patient-portal-nav ${navCollapsed ? 'collapsed' : ''}`}>
                <div className="patient-portal-nav__logo">
                    <span className="patient-portal-nav__icon">C</span>
                    <span className="patient-portal-nav__title">CDSS Patient</span>
                </div>
                <nav className="patient-portal-nav__links">
                    {patientNavItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.end}
                            className={({ isActive }) => `patient-portal-nav__link${isActive ? ' active' : ''}`}
                        >
                            <span className="sidebar__link-icon">{item.icon}</span>
                            <span className="sidebar__link-text">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>
                <div className="patient-portal-nav__footer">
                    <button type="button" className="patient-portal-nav__footer-btn" onClick={handleLogout}>
                        <span className="sidebar__link-icon">🔓</span>
                        <span className="sidebar__link-text">Logout</span>
                    </button>
                    <div className="patient-portal-nav__footer-divider" />
                    <button
                        type="button"
                        className="patient-portal-nav__footer-btn"
                        onClick={() => setNavCollapsed((v) => !v)}
                        aria-label={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}
                        title={navCollapsed ? 'Expand' : 'Collapse'}
                    >
                        <span className="sidebar__link-icon">{navCollapsed ? '▶' : '◀'}</span>
                        <span className="sidebar__link-text">{navCollapsed ? '' : 'Collapse'}</span>
                    </button>
                </div>
            </aside>
            <div className="patient-portal-main">
                <header className="patient-portal-header">
                    <div className="patient-portal-header__branding">
                        <div className="patient-portal-header__name">{user?.name || 'Patient'}</div>
                        <div className="patient-portal-header__id">
                            {user?.id ? `${t(language, 'header_patientId')}: ${user.id}` : '—'}
                        </div>
                    </div>
                    <div className="patient-portal-header__actions">
                        <div className="patient-portal-lang" role="group" aria-label="Language selection">
                            {LANG_OPTIONS.map((opt) => (
                                <button
                                    key={opt.id}
                                    type="button"
                                    className={`patient-portal-lang__btn${language === opt.id ? ' is-active' : ''}`}
                                    onClick={() => handleLanguageChange(opt.id)}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>
                </header>
                <div className="patient-portal-main__content">
                    <Outlet context={{ language }} />
                </div>
            </div>
        </div>
    );
}
