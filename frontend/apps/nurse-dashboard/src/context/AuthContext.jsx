import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const roles = { DOCTOR: 'doctor', SURGEON: 'surgeon', NURSE: 'nurse', ADMIN: 'admin' };

const users = [
  { id: 'u1', name: 'Dr. Priya Sharma', role: roles.DOCTOR, email: 'priya@cdss.ai', password: 'mock' },
  { id: 'u2', name: 'Dr. Vikram Patel', role: roles.SURGEON, email: 'vikram@cdss.ai', password: 'mock' },
  { id: 'u3', name: 'Nurse Anjali', role: roles.NURSE, email: 'anjali@cdss.ai', password: 'mock' },
  { id: 'u4', name: 'Admin Sameer', role: roles.ADMIN, email: 'admin@cdss.ai', password: 'mock' },
];

const CDSS_USER_KEY = 'cdss_nurse_user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem(CDSS_USER_KEY);
    if (saved) try { setUser(JSON.parse(saved)); } catch (_) {}
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const found = users.find(u => u.email === email && u.password === password);
    if (found) {
      const { password: _, ...u } = found;
      setUser({ ...u, token: u.id });
      localStorage.setItem(CDSS_USER_KEY, JSON.stringify({ ...u, token: u.id }));
      return { success: true };
    }
    return { success: false, message: 'Invalid credentials' };
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(CDSS_USER_KEY);
  };

  const hasRole = (r) => !!(user && (Array.isArray(r) ? r.includes(user.role) : user.role === r));

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
