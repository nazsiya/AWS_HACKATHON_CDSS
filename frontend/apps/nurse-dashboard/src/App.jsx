import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import Sidebar from './components/Sidebar/Sidebar';
import Header from './components/Header/Header';
import Dashboard from './pages/Dashboard/Dashboard';
import Patients from './pages/Patients/Patients';
import Vitals from './pages/Vitals/Vitals';
import Medications from './pages/Medications/Medications';
import Schedule from './pages/Schedule/Schedule';
import Login from './pages/Login/Login';
import { roles } from './context/AuthContext';
import './App.css';

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-content">
        <Header />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<ProtectedRoute requiredRoles={[roles.NURSE, roles.ADMIN]}><Dashboard /></ProtectedRoute>} />
            <Route path="/patients" element={<ProtectedRoute requiredRoles={[roles.NURSE, roles.ADMIN]}><Patients /></ProtectedRoute>} />
            <Route path="/vitals" element={<ProtectedRoute requiredRoles={[roles.NURSE, roles.ADMIN]}><Vitals /></ProtectedRoute>} />
            <Route path="/medications" element={<ProtectedRoute requiredRoles={[roles.NURSE, roles.ADMIN]}><Medications /></ProtectedRoute>} />
            <Route path="/schedule" element={<ProtectedRoute requiredRoles={[roles.NURSE, roles.ADMIN]}><Schedule /></ProtectedRoute>} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={<AppLayout />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;
