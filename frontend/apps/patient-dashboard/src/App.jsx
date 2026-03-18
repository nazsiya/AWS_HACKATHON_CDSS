import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import PatientPortalLayout from './components/PatientPortal/PatientPortalLayout';
import PatientPortalHome from './pages/PatientPortal/PatientPortalHome';
import PatientPortalSummary from './pages/PatientPortal/PatientPortalSummary';
import PatientPortalMedications from './pages/PatientPortal/PatientPortalMedications';
import PatientPortalAppointments from './pages/PatientPortal/PatientPortalAppointments';
import Login from './pages/Login/Login';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <ProtectedRoute>
                <PatientPortalLayout />
              </ProtectedRoute>
            }>
              <Route index element={<PatientPortalHome />} />
              <Route path="summary" element={<PatientPortalSummary />} />
              <Route path="medication-tracker" element={<PatientPortalMedications />} />
              <Route path="appointments" element={<PatientPortalAppointments />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;
