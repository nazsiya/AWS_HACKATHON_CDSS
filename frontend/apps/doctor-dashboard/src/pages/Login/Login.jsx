import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Login.css';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from?.pathname || '/';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError('');

        try {
            const result = await login(email, password);
            if (result.success) {
                const role = result.user?.role;
                const isPatient = role === 'patient';
                const targetPath = isPatient ? '/patient-portal' : (from || '/');
                navigate(targetPath, { replace: true });
            } else {
                setError(result.message || 'Login failed');
            }
        } catch (_) {
            setError('Connection error. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card-section animate-in">
                <div className="login-header">
                    <h1>Clinical Decision Support System</h1>
                    <p>Secure Medical Dashboard Access</p>
                </div>

                <div className="login-card">
                    <form onSubmit={handleSubmit} className="login-form">
                        <div className="form-group">
                            <label htmlFor="email">User ID</label>
                            <input
                                id="email"
                                type="email"
                                placeholder="Enter your user ID"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                type="password"
                                placeholder="Enter password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>

                        <a href="/forgot-password" className="forgot-password">
                            Forgot Password?
                        </a>

                        {error && <div className="login-error">⚠️ {error}</div>}

                        <button type="submit" className="login-btn" disabled={isSubmitting}>
                            {isSubmitting ? 'Authenticating...' : 'Login to Dashboard'}
                        </button>
                    </form>
                </div>

                <div className="login-footer">
                    <h3>CDSS Platform © 2026</h3>
                    <p>AI Assisted Clinical Decision Support System</p>
                </div>
            </div>
        </div>
    );
}
