import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import './PatientPortal.css';

export default function PatientPortal() {
    const { user } = useAuth();
    const [vitals, setVitals] = useState({ bp: '120/80', hr: '72', spo2: '98' });

    return (
        <div className="patient-portal page-enter">
            <header className="portal-header">
                <h1 className="portal-title">Welcome, {user?.name || 'Patient'}</h1>
                <span className="portal-subtitle">Your Health at a Glance</span>
            </header>

            <div className="portal-grid">
                <div className="portal-card glass">
                    <h2 className="card-title">💓 Current Vitals</h2>
                    <div className="vitals-summary">
                        <div className="vital-item">
                            <span className="vital-label">BP</span>
                            <span className="vital-value">{vitals.bp}</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">HR</span>
                            <span className="vital-value">{vitals.hr} bpm</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">SpO2</span>
                            <span className="vital-value">{vitals.spo2}%</span>
                        </div>
                    </div>
                </div>

                <div className="portal-card glass">
                    <h2 className="card-title">💊 Next Medication</h2>
                    <div className="med-info">
                        <div className="med-name">Metformin 500mg</div>
                        <div className="med-time">Due in 2 hours (08:00 PM)</div>
                    </div>
                </div>

                <div className="portal-card portal-card--full glass">
                    <h2 className="card-title">📅 Upcoming Appointments</h2>
                    <div className="appointment-list">
                        <div className="appointment-item">
                            <div className="app-info">
                                <div className="app-doctor">Dr. Priya Sharma</div>
                                <div className="app-type">Cardiology Consultation</div>
                            </div>
                            <div className="app-time">Tomorrow, 10:30 AM</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="portal-actions">
                <button className="btn btn--primary">Request Consultation</button>
                <button className="btn btn--outline">Download Lab Results</button>
            </div>
        </div>
    );
}
