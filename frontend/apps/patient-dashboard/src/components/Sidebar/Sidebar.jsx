import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './Sidebar.css';

const navItems = [
  { section: 'My Health' },
  { path: '/', icon: '🏠', label: 'Dashboard', tooltip: 'Dashboard' },
  { path: '/appointments', icon: '📅', label: 'My Appointments', tooltip: 'Appointments' },
  { path: '/medications', icon: '💊', label: 'My Medications', tooltip: 'Medications' },
  { path: '/records', icon: '📋', label: 'My Records', tooltip: 'Health records' },
  { section: 'Support' },
  { path: '/contact', icon: '💬', label: 'Contact & Messages', tooltip: 'Contact' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="sidebar__logo">
        <div className="sidebar__logo-icon">C</div>
        <div className="sidebar__logo-text">
          <span className="sidebar__logo-title">CDSS</span>
          <span className="sidebar__logo-subtitle">Patient Portal</span>
        </div>
      </div>
      <nav className="sidebar__nav">
        {navItems.map((item, i) => {
          if (item.section) {
            return <div key={`s-${i}`} className="sidebar__section-label">{item.section}</div>;
          }
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `sidebar__link${isActive ? ' active' : ''}`}
              data-tooltip={item.tooltip}
            >
              <span className="sidebar__link-icon">{item.icon}</span>
              <span className="sidebar__link-text">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="sidebar__footer">
        <button className="sidebar__link logout-btn" onClick={handleLogout} style={{ width: '100%', background: 'none', border: 'none', padding: 'var(--space-3)', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <span className="sidebar__link-icon">🚪</span>
          <span className="sidebar__link-text">Logout</span>
        </button>
        <button className="sidebar__collapse-btn" onClick={() => setCollapsed(!collapsed)}>
          <span className="sidebar__collapse-icon">{collapsed ? '▶' : '◀'}</span>
          <span className="sidebar__link-text">{collapsed ? '' : 'Collapse'}</span>
        </button>
      </div>
    </aside>
  );
}
