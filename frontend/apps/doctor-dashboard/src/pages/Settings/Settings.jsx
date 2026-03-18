import { useState, useEffect } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { currentDoctor } from '../../data/mockData';
import './Settings.css';

const SUMMARY_LANG_KEY = 'cdss_summary_lang';

export default function Settings() {
    const { theme, toggleTheme } = useTheme();
    const [summaryLang, setSummaryLang] = useState(() => localStorage.getItem(SUMMARY_LANG_KEY) || 'en');
    const [notifications, setNotifications] = useState(true);
    const [aiAssist, setAiAssist] = useState(true);
    const [voiceInput, setVoiceInput] = useState(false);

    return (
        <div className="settings-page page-enter">
            <h1 className="settings-page__title">⚙️ Settings</h1>

            {/* Profile Section */}
            <div className="settings-section animate-in">
                <div className="settings-section__header">👤 Profile</div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Name</span>
                        <span className="settings-item__desc">{currentDoctor.name}</span>
                    </div>
                </div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Department</span>
                        <span className="settings-item__desc">{currentDoctor.department}</span>
                    </div>
                </div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Specialization</span>
                        <span className="settings-item__desc">{currentDoctor.specialization}</span>
                    </div>
                </div>
            </div>

            {/* Appearance */}
            <div className="settings-section animate-in animate-in-delay-1">
                <div className="settings-section__header">🎨 Appearance</div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Dark Mode</span>
                        <span className="settings-item__desc">Switch between light and dark theme</span>
                    </div>
                    <div className={`toggle ${theme === 'dark' ? 'active' : ''}`} onClick={toggleTheme}>
                        <div className="toggle__knob" />
                    </div>
                </div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Language</span>
                        <span className="settings-item__desc">Interface and summary language for AI outputs</span>
                    </div>
                    <select
                        className="settings-select"
                        value={summaryLang}
                        onChange={(e) => {
                            const v = e.target.value;
                            setSummaryLang(v);
                            localStorage.setItem(SUMMARY_LANG_KEY, v);
                        }}
                    >
                        <option value="en">English</option>
                        <option value="hi">Hindi</option>
                        <option value="ta">Tamil</option>
                        <option value="te">Telugu</option>
                        <option value="bn">Bengali</option>
                    </select>
                </div>
            </div>

            {/* Notifications */}
            <div className="settings-section animate-in animate-in-delay-2">
                <div className="settings-section__header">🔔 Notifications</div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Push Notifications</span>
                        <span className="settings-item__desc">Receive alerts for critical patients</span>
                    </div>
                    <div className={`toggle ${notifications ? 'active' : ''}`} onClick={() => setNotifications(!notifications)}>
                        <div className="toggle__knob" />
                    </div>
                </div>
            </div>

            {/* AI Settings */}
            <div className="settings-section animate-in animate-in-delay-3">
                <div className="settings-section__header">🤖 AI Assistant</div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">AI-Assisted Consultation</span>
                        <span className="settings-item__desc">Show AI suggestions during consultations</span>
                    </div>
                    <div className={`toggle ${aiAssist ? 'active' : ''}`} onClick={() => setAiAssist(!aiAssist)}>
                        <div className="toggle__knob" />
                    </div>
                </div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">Voice Input</span>
                        <span className="settings-item__desc">Enable microphone for voice commands</span>
                    </div>
                    <div className={`toggle ${voiceInput ? 'active' : ''}`} onClick={() => setVoiceInput(!voiceInput)}>
                        <div className="toggle__knob" />
                    </div>
                </div>
                <div className="settings-item">
                    <div className="settings-item__info">
                        <span className="settings-item__label">AI Model</span>
                        <span className="settings-item__desc">Select the AI model for CDSS</span>
                    </div>
                    <select className="settings-select">
                        <option>Claude 3 Haiku (Fast)</option>
                        <option>Claude 3 Sonnet (Balanced)</option>
                        <option>Claude 3 Opus (Powerful)</option>
                    </select>
                </div>
            </div>
        </div>
    );
}
