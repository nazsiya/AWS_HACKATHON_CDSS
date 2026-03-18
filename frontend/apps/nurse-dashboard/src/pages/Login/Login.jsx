import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = useLocation().state?.from?.pathname || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    const result = await login(email, password);
    if (result.success) navigate(from, { replace: true });
    else setError(result.message || 'Login failed');
    setIsSubmitting(false);
  };

  return (
    <div className="login-container">
      <div className="login-card animate-in">
        <div className="login-logo">
          <div className="logo-icon">C</div>
          <h1>CDSS Nurse Dashboard</h1>
          <p>Patient care & vitals</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Email</label>
            <input type="email" placeholder="nurse@hospital.ai" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <div className="login-error">⚠️ {error}</div>}
          <button type="submit" className="login-btn" disabled={isSubmitting}>{isSubmitting ? 'Signing in...' : 'Sign in'}</button>
        </form>
        <div className="login-footer">
          <div className="demo-hint"><small>Contact team for demo access</small></div>
        </div>
      </div>
    </div>
  );
}
