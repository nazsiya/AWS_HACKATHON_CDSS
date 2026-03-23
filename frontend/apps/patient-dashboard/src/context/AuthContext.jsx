import { createContext, useContext, useState, useEffect } from 'react';
import { isCognitoEnabled } from '../api/config';

const AuthContext = createContext();

export const roles = {
  PATIENT: 'patient',
  DOCTOR: 'doctor',
  SURGEON: 'surgeon',
  NURSE: 'nurse',
  ADMIN: 'admin',
};

// Local mock users — used only when Cognito is disabled (no VITE_COGNITO_*). Patient demo matches team guide password.
const users = [
  { id: 'p1', name: 'Rahul Kumar', role: roles.PATIENT, email: 'patient@cdss.ai', password: 'Demo@1234' },
  { id: 'u1', name: 'Dr. Priya Sharma', role: roles.DOCTOR, email: 'priya@cdss.ai', password: 'mock' },
  { id: 'u2', name: 'Dr. Vikram Patel', role: roles.SURGEON, email: 'vikram@cdss.ai', password: 'mock' },
  { id: 'u3', name: 'Nurse Anjali', role: roles.NURSE, email: 'anjali@cdss.ai', password: 'mock' },
  { id: 'u4', name: 'Admin Sameer', role: roles.ADMIN, email: 'admin@cdss.ai', password: 'mock' },
];

const CDSS_USER_KEY = 'cdss_user';
const CDSS_TOKEN_KEY = 'cdss_token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isCognitoEnabled()) {
      import('../lib/cognito').then(({ cognitoGetSession }) => {
        cognitoGetSession()
          .then((sessionUser) => {
            if (sessionUser) {
              setUser(sessionUser);
              localStorage.setItem(CDSS_USER_KEY, JSON.stringify(sessionUser));
            }
            setLoading(false);
          })
          .catch(() => setLoading(false));
      }).catch(() => setLoading(false));
      return;
    }
    const saved = localStorage.getItem(CDSS_USER_KEY);
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch (_) { /* ignore */ }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    if (isCognitoEnabled()) {
      try {
        const { cognitoSignIn } = await import('../lib/cognito');
        const sessionUser = await cognitoSignIn(email, password);
        setUser(sessionUser);
        localStorage.setItem(CDSS_USER_KEY, JSON.stringify(sessionUser));
        return { success: true, user: sessionUser };
      } catch (err) {
        const message =
          err?.name === 'NotAuthorizedException' ? 'Invalid credentials' : (err?.message || 'Login failed');
        return { success: false, message };
      }
    }
    const found = users.find((u) => u.email === email && u.password === password);
    if (found) {
      const { password: _, ...u } = found;
      setUser({ ...u, token: u.id });
      localStorage.setItem(CDSS_USER_KEY, JSON.stringify({ ...u, token: u.id }));
      return { success: true };
    }
    return { success: false, message: 'Invalid credentials' };
  };

  const logout = async () => {
    if (isCognitoEnabled()) {
      try {
        const { cognitoSignOut } = await import('../lib/cognito');
        await cognitoSignOut();
      } catch (_) { /* ignore */ }
    }
    setUser(null);
    localStorage.removeItem(CDSS_USER_KEY);
    localStorage.removeItem(CDSS_TOKEN_KEY);
  };

  const hasRole = (requiredRoles) => {
    if (!user) return false;
    return Array.isArray(requiredRoles) ? requiredRoles.includes(user.role) : user.role === requiredRoles;
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
