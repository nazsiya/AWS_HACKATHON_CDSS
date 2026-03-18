import { useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { setAuthTokenGetter } from '../../api/client';

/**
 * Connects AuthContext to the API client so every request can send the JWT.
 * When using Cognito, user.token will be the idToken/accessToken.
 */
export default function AuthApiBridge({ children }) {
  const { user } = useAuth();

  useEffect(() => {
    setAuthTokenGetter(() => (user?.token ?? user?.id ?? null));
  }, [user]);

  return children;
}
