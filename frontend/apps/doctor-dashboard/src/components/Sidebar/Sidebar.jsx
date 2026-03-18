import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth, roles } from '../../context/AuthContext';
import './Sidebar.css';

/** Admin dashboard sidebar: Dashboard, Patients, Doctors, Appointments, Reports, Analytics, Settings */
const adminNavItems = [
    { path: '/', icon: '📊', label: 'Dashboard', tooltip: 'Dashboard' },
    { path: '/patients', icon: '👥', label: 'Patients', tooltip: 'Patients' },
    { path: '/doctors', icon: '🩺', label: 'Doctors', tooltip: 'Doctors' },
    { path: '/appointments', icon: '📅', label: 'Appointments', tooltip: 'Appointments' },
    { path: '/ai', icon: '🤖', label: 'AI Assistant', tooltip: 'AI Assistant' },
    { path: '/reports', icon: '📄', label: 'Reports', tooltip: 'Reports' },
    { path: '/admin/analytics', icon: '📈', label: 'Analytics', tooltip: 'Analytics' },
    { path: '/settings', icon: '⚙️', label: 'Settings', tooltip: 'Settings' },
];

/** Doctor dashboard sidebar */
const doctorNavItems = [
    { path: '/', icon: '🎛️', label: 'Dashboard', tooltip: 'Dashboard' },
    { path: '/schedule', icon: '📅', label: 'Appointments', tooltip: 'Appointments' },
    { path: '/patients', icon: '👥', label: 'Patients', tooltip: 'Patients' },
    { path: '/ai', icon: '🤖', label: 'AI Assistant', tooltip: 'AI Assistant' },
    { path: '/surgery', icon: '🏥', label: 'Surgery', tooltip: 'Surgery' },
];

import { currentDoctor } from '../../data/mockData';

export default function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);
    const { user, hasRole, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const isAdmin = hasRole && hasRole([roles.ADMIN, roles.SUPERUSER]);
    const navItems = isAdmin ? adminNavItems : doctorNavItems;

    const displayName = user?.name || currentDoctor?.name || 'Doctor';
    const displayInitials = user?.name ? user.name.split(' ').map((n) => n[0]).join('') : (currentDoctor?.initials || 'D');

    return (
        <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
            {/* Profile Section */}
            <div className="sidebar__profile">
                <div className="sidebar__avatar-wrap">
                    <div className="sidebar__avatar-initials">
                        {displayInitials}
                    </div>
                </div>
                {!collapsed && (
                    <div className="sidebar__profile-info">
                        <h3 className="sidebar__doctor-name">{displayName}</h3>
                        <p className="sidebar__doctor-title">{user?.role === roles.SUPERUSER ? 'Super Administrator' : user?.role === roles.ADMIN ? 'Administrator' : 'Primary care doctor'}</p>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="sidebar__nav">
                {navItems.map((item) => (
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
                ))}
            </nav>

            {/* Footer with Logout */}
            <div className="sidebar__footer">
                <button className="sidebar__link logout-btn" onClick={handleLogout}>
                    <span className="sidebar__link-icon">🔓</span>
                    <span className="sidebar__link-text">Logout</span>
                </button>
                <div className="sidebar__divider" />
                <button className="sidebar__collapse-btn" onClick={() => setCollapsed(!collapsed)}>
                    <span className="sidebar__collapse-icon">{collapsed ? '▶' : '◀'}</span>
                    <span className="sidebar__link-text">{collapsed ? '' : 'Collapse'}</span>
                </button>
            </div>

            {!collapsed && (
                <div className="sidebar__copyright">
                    © 2026 CDSS. All Rights Reserved
                </div>
            )}
        </aside>
    );
}

