import { useState } from 'react';
import { Link } from 'react-router-dom';
import './ForgotPassword.css';

/**
 * Forgot Password — Request reset link (UI only; backend can wire later).
 */
export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);
        // Placeholder: in production, call API to send reset email
        setTimeout(() => {
            setSent(true);
            setIsSubmitting(false);
        }, 800);
    };

    return (
        <div className="forgot-screen-root">
            <div className="forgot-hero">
                <h1 className="forgot-hero-title">Reset Password</h1>
                <p className="forgot-hero-subtitle">
                    Enter your User ID or email and we'll send you a link to reset your password.
                </p>
            </div>

            <div className="forgot-card">
                {sent ? (
                    <div className="forgot-success">
                        <p className="forgot-success-title">Check your inbox</p>
                        <p className="forgot-success-text">
                            If an account exists for <strong>{email || 'that address'}</strong>, you will receive password reset instructions shortly.
                        </p>
                        <Link to="/login" className="forgot-back-link">Back to Login</Link>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="forgot-form">
                        <div className="forgot-field">
                            <label htmlFor="forgot-email">User ID / Email</label>
                            <input
                                id="forgot-email"
                                type="text"
                                placeholder="Enter your user ID or email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                autoComplete="username"
                            />
                        </div>
                        {error && <div className="forgot-error" role="alert">{error}</div>}
                        <button type="submit" className="forgot-btn" disabled={isSubmitting}>
                            {isSubmitting ? 'Sending...' : 'Send reset link'}
                        </button>
                        <Link to="/login" className="forgot-back-link">Back to Login</Link>
                    </form>
                )}
            </div>

            <footer className="forgot-footer">
                <p className="forgot-footer-copy">CDSS Platform © 2026</p>
                <p className="forgot-footer-tagline">AI Assisted Clinical Decision Support System</p>
            </footer>
        </div>
    );
}
