import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, roles } from './context/AuthContext';
import AuthApiBridge from './components/Auth/AuthApiBridge';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary';
import Sidebar from './components/Sidebar/Sidebar';
import Header from './components/Header/Header';
import Dashboard from './pages/Dashboard/Dashboard';
import Patients from './pages/Patients/Patients';
import PatientConsultation from './pages/PatientConsultation/PatientConsultation';
import AIChat from './pages/AIChat/AIChat';
import Surgery from './pages/Surgery/Surgery';
import SurgeryPlanning from './pages/SurgeryPlanning/SurgeryPlanning';
import Medications from './pages/Medications/Medications';
import Schedule from './pages/Schedule/Schedule';
import Doctors from './pages/Doctors/Doctors';
import Appointments from './pages/Appointments/Appointments';
import AdminUsers from './pages/Admin/AdminUsers';
import AdminDashboard from './pages/Admin/AdminDashboard';
import AdminAudit from './pages/Admin/AdminAudit';
import AdminConfig from './pages/Admin/AdminConfig';
import AdminAnalytics from './pages/Admin/AdminAnalytics';
import AdminResources from './pages/Admin/AdminResources';
import Settings from './pages/Settings/Settings';
import Resources from './pages/Resources/Resources';
import Reports from './pages/Reports/Reports';
import Profile from './pages/Profile/Profile';
import Login from './pages/Login/Login';
import DoctorModuleGuard from './components/Auth/DoctorModuleGuard';
import PatientPortalGuard from './components/Auth/PatientPortalGuard';
import { ActivityProvider } from './context/ActivityContext';
import PatientPortalLayout from './components/PatientPortal/PatientPortalLayout';
import PatientPortalHome from './pages/PatientPortal/PatientPortalHome';
import PatientPortalHistory from './pages/PatientPortal/PatientPortalHistory';
import PatientPortalMedications from './pages/PatientPortal/PatientPortalMedications';
import PatientPortalSummary from './pages/PatientPortal/PatientPortalSummary';
import PatientPortalAppointments from './pages/PatientPortal/PatientPortalAppointments';
import Notifications from './pages/Notifications/Notifications';
import MyActivity from './pages/MyActivity/MyActivity';
import ApiHealthBanner from './components/ApiHealthBanner/ApiHealthBanner';
import './App.css';

function AppLayout() {
  return (
    <div className="app-layout">
      <ApiHealthBanner />
      <Sidebar />
      <div className="app-content">
        <Header />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/activity" element={<ProtectedRoute><MyActivity /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
            <Route path="/patients" element={<ProtectedRoute><Patients /></ProtectedRoute>} />
            <Route path="/doctors" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <Doctors />
              </ProtectedRoute>
            } />
            <Route path="/appointments" element={<ProtectedRoute><Appointments /></ProtectedRoute>} />
            <Route path="/patient/:patientId" element={<ProtectedRoute><PatientConsultation /></ProtectedRoute>} />
            <Route path="/ai" element={<ProtectedRoute><AIChat /></ProtectedRoute>} />
            <Route path="/surgery" element={<ProtectedRoute><Surgery /></ProtectedRoute>} />
            <Route path="/surgery-planning/:surgeryId" element={
              <ProtectedRoute requiredRoles={['surgeon', 'admin']}>
                <SurgeryPlanning />
              </ProtectedRoute>
            } />
            <Route path="/medications" element={<ProtectedRoute><Medications /></ProtectedRoute>} />
            <Route path="/clinical-workboard" element={<ProtectedRoute><Medications /></ProtectedRoute>} />
            <Route path="/schedule" element={<ProtectedRoute><Schedule /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
            <Route path="/resources" element={<ProtectedRoute><Resources /></ProtectedRoute>} />
            <Route path="/admin/users" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <AdminUsers />
              </ProtectedRoute>
            } />
            <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="/admin/audit" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <AdminAudit />
              </ProtectedRoute>
            } />
            <Route path="/admin/config" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <AdminConfig />
              </ProtectedRoute>
            } />
            <Route path="/admin/analytics" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <AdminAnalytics />
              </ProtectedRoute>
            } />
            <Route path="/admin/resources" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <AdminResources />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                <Settings />
              </ProtectedRoute>
            } />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider>
          <AuthApiBridge>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<Login />} />
                {/* Admin Dashboard — standalone full-viewport layout (no sidebar/header) */}
                <Route path="/admin/dashboard" element={
                  <DoctorModuleGuard>
                    <ProtectedRoute requiredRoles={[roles.ADMIN, roles.SUPERUSER]}>
                      <AdminDashboard />
                    </ProtectedRoute>
                  </DoctorModuleGuard>
                } />
                <Route path="/patient-portal" element={
                  <PatientPortalGuard>
                    <PatientPortalLayout />
                  </PatientPortalGuard>
                }>
                  <Route index element={<PatientPortalHome />} />
                  <Route path="summary" element={<PatientPortalSummary />} />
                  <Route path="medication-tracker" element={<PatientPortalMedications />} />
                  <Route path="appointments" element={<PatientPortalAppointments />} />
                  <Route path="history" element={<PatientPortalAppointments />} />
                  <Route path="medications" element={<PatientPortalMedications />} />
                </Route>
                <Route path="/*" element={
                  <DoctorModuleGuard>
                    <ActivityProvider>
                      <AppLayout />
                    </ActivityProvider>
                  </DoctorModuleGuard>
                } />
              </Routes>
            </BrowserRouter>
          </AuthApiBridge>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
