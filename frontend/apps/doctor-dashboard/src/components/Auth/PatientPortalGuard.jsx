import { Navigate } from 'react-router-dom';
import { useAuth, roles } from '../../context/AuthContext';

/**
 * Restricts Patient Portal to users with role=patient only.
 * Staff (doctor, nurse, admin, surgeon) are redirected to the doctor dashboard.
 */
export default function PatientPortalGuard({ children }) {
    const { user, loading } = useAuth();

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
    if (!user) return <Navigate to="/login" replace />;
    if (user.role !== roles.PATIENT) return <Navigate to="/" replace />;

    return children;
}
