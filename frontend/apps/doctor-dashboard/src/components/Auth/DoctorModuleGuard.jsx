import { Navigate } from 'react-router-dom';
import { useAuth, roles } from '../../context/AuthContext';

/**
 * Wraps the Doctor Module (AppLayout). If the user is logged in with role=patient,
 * redirects to Patient Portal so patients cannot access doctor routes.
 */
export default function DoctorModuleGuard({ children }) {
    const { user, loading } = useAuth();

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
    if (!user) return <Navigate to="/login" replace />;
    if (user.role === roles.PATIENT) return <Navigate to="/patient-portal" replace />;

    return children;
}
