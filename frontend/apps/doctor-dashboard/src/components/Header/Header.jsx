import React, { useState, useRef, useEffect } from 'react';
import { useAuth, roles } from '../../context/AuthContext';
import { useLocation, useNavigate } from 'react-router-dom';
import './Header.css';

const pathLabels = {
  '/': 'Dashboard',
  '/activity': 'My Activity',
  '/patients': 'Patients',
  '/patient': 'Patient Detail',
  '/surgery': 'Surgeries',
  '/resources': 'Resources',
  '/medications': 'Clinical Tasks',
  '/reports': 'Reports',
  '/profile': 'Profile',
  '/admin/users': 'Users',
  '/admin/dashboard': 'Admin Dashboard',
  '/admin/audit': 'Audit Log',
  '/admin/config': 'System Config',
  '/admin/analytics': 'Analytics',
  '/admin/resources': 'Admin Resources',
  '/settings': 'Settings',
};

const MOCK_NOTIFICATIONS = [
  { id: '1', title: 'New appointment scheduled', body: 'John Doe — Tomorrow 10:00 AM', time: '2 min ago', unread: true },
  { id: '2', title: 'Lab results ready', body: 'Patient Ananya Singh — CBC report available', time: '15 min ago', unread: true },
  { id: '3', title: 'Surgery reminder', body: 'Pre-op check for Mohammed Farhan at 2:00 PM', time: '1 hour ago', unread: false },
  { id: '4', title: 'System update', body: 'CDSS dashboard updated to latest version.', time: 'Yesterday', unread: false },
];

function Breadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(Boolean);
  if (pathnames.length === 0) {
    return (
      <nav className="header__breadcrumbs" aria-label="Breadcrumb">
        <span className="header__breadcrumb-item">Doctor Portal</span>
        <span className="header__breadcrumb-sep"> / </span>
        <span className="header__breadcrumb-item">Dashboard</span>
        <span className="header__breadcrumb-sep"> / </span>
        <span className="header__breadcrumb-item">My Activity</span>
      </nav>
    );
  }
  let current = '';
  const segments = pathnames.map((segment, i) => {
    current += (i === 0 ? '' : '/') + segment;
    const label = pathLabels[`/${current}`] || pathLabels[`/${segment}`] || segment;
    return { path: current, label };
  });
  if (pathnames[0] === 'patient' && pathnames[1]) {
    segments[segments.length - 1] = { path: location.pathname, label: `Patient ${pathnames[1]}` };
  }
  return (
    <nav className="header__breadcrumbs" aria-label="Breadcrumb">
      <span className="header__breadcrumb-item">Doctor Portal</span>
      <span className="header__breadcrumb-sep"> / </span>
      <span className="header__breadcrumb-item">Dashboard</span>
      {segments.map((s) => (
        <span key={s.path}>
          <span className="header__breadcrumb-sep"> / </span>
          <span className="header__breadcrumb-item">{s.label}</span>
        </span>
      ))}
    </nav>
  );
}

export default function Header() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [notificationOpen, setNotificationOpen] = useState(false);
  const notificationRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    if (!notificationOpen) return;
    const handleClickOutside = (e) => {
      if (notificationRef.current && !notificationRef.current.contains(e.target)) {
        setNotificationOpen(false);
      }
    };
    const handleEscape = (e) => {
      if (e.key === 'Escape') setNotificationOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [notificationOpen]);

  const focusSearch = () => searchInputRef.current?.focus();

  if (!user) return null;

  const initials = user.name.split(' ').map((n) => n[0]).join('');

  return (
    <header className="header header--ops">
      <div className="header__inner">
        <div className="header__left">
          <h1 className="header__title">{user.role === roles.ADMIN || user.role === roles.SUPERUSER ? 'CDSS DASHBOARD' : 'Doctor Portal'}</h1>
          {user.role !== roles.ADMIN && user.role !== roles.SUPERUSER && <Breadcrumbs />}
        </div>

        {/* Center: Search — label makes icon + area focus input for accessibility */}
        <div className="header__center" role="search" aria-label="Search">
          <label className="header__search-label" htmlFor="header-search-input" onClick={focusSearch}>
            <span className="header__search-icon" aria-hidden="true">🔍</span>
            <input
              ref={searchInputRef}
              id="header-search-input"
              className="header__search-input"
              type="search"
              placeholder="Search patients..."
              aria-label="Search patients, appointments, and cases"
              autoComplete="off"
            />
          </label>
        </div>

        {/* Right: Notification dropdown, Profile */}
        <div className="header__right">
          <div className="header__notify-wrap" ref={notificationRef}>
            <button
              type="button"
              className="header__icon-btn header__icon-btn--notify"
              title="Notifications"
              aria-label="Open notifications"
              aria-expanded={notificationOpen}
              aria-haspopup="true"
              aria-controls="header-notification-panel"
              onClick={() => setNotificationOpen((o) => !o)}
            >
              <span className="header__icon" aria-hidden="true">🔔</span>
              <span className="header__notify-dot" aria-hidden="true" />
            </button>

            {notificationOpen && (
              <div
                id="header-notification-panel"
                className="header__notification-panel"
                role="region"
                aria-label="Notification feed"
              >
                <div className="header__notification-head">
                  <span className="header__notification-title">Notifications</span>
                </div>
                <ul className="header__notification-list">
                  {MOCK_NOTIFICATIONS.map((n) => (
                    <li key={n.id} className={`header__notification-item ${n.unread ? 'header__notification-item--unread' : ''}`}>
                      <div className="header__notification-item-title">{n.title}</div>
                      <div className="header__notification-item-body">{n.body}</div>
                      <div className="header__notification-item-time">{n.time}</div>
                    </li>
                  ))}
                </ul>
                <div className="header__notification-foot">
                  <button
                    type="button"
                    className="header__notification-link"
                    onClick={() => {
                      setNotificationOpen(false);
                      navigate('/notifications');
                    }}
                  >
                    View all
                  </button>
                </div>
              </div>
            )}
          </div>
          <div className="header__profile">
            <div className="header__avatar" aria-hidden="true">{initials}</div>
            <div className="header__profile-info">
              <span className="header__profile-name">{user.name}</span>
              <span className="header__profile-role">{user.role || 'Admin'}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

