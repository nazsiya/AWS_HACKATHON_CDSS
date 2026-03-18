import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import './Header.css';

export default function Header() {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  if (!user) return null;
  const initials = user.name.split(' ').map(n => n[0]).join('');
  return (
    <header className="header">
      <div className="header__left">
        <div className="header__greeting">
          <span className="header__greeting-text">Nurse station —</span>
          <span className="header__greeting-name">{user.name}</span>
        </div>
      </div>
      <div className="header__right">
        <button className="header__theme-btn" onClick={toggleTheme}>{theme === 'light' ? '🌙' : '☀️'}</button>
        <div className="header__divider" />
        <div className="header__profile">
          <div className="header__avatar">{initials}</div>
          <div className="header__profile-info">
            <span className="header__profile-name">{user.name}</span>
            <span className="header__profile-role">Nurse</span>
          </div>
        </div>
      </div>
    </header>
  );
}
