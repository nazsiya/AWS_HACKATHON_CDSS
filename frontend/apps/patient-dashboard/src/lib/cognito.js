/**
 * Cognito auth helper for patient portal.
 * Only used when VITE_COGNITO_USER_POOL_ID and VITE_COGNITO_CLIENT_ID are set.
 */
import { Amplify } from 'aws-amplify';
import { signIn, getCurrentUser, signOut as amplifySignOut } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import { config, isCognitoEnabled } from '../api/config';

let configured = false;

function ensureConfigured() {
  if (configured) return;
  if (!isCognitoEnabled()) return;
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.cognito.userPoolId,
        userPoolClientId: config.cognito.clientId,
        region: config.cognito.region,
      },
    },
  });
  configured = true;
}

export async function cognitoSignIn(email, password) {
  ensureConfigured();
  await signIn({ username: email, password });
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken;
  const jwt = idToken?.toString();
  const payload = idToken?.payload || {};
  const role = payload['custom:role'] || payload.role || 'patient';
  const name = payload.name || payload['cognito:username'] || email;
  const patientId = payload['custom:patientId'] || payload.patientId || payload.sub || '';
  return {
    id: payload.sub || email,
    name,
    email,
    role: role.toLowerCase(),
    patientId,
    token: jwt,
  };
}

export async function cognitoGetSession() {
  if (!isCognitoEnabled()) return null;
  ensureConfigured();
  try {
    const user = await getCurrentUser();
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken;
    const jwt = idToken?.toString();
    const payload = idToken?.payload || {};
    const role = payload['custom:role'] || payload.role || 'patient';
    const patientId = payload['custom:patientId'] || payload.patientId || payload.sub || '';
    return {
      id: payload.sub || user?.userId,
      name: payload.name || user?.username || '',
      email: payload.email || user?.signInDetails?.loginId || '',
      role: role.toLowerCase(),
      patientId,
      token: jwt,
    };
  } catch {
    return null;
  }
}

export async function cognitoSignOut() {
  if (!isCognitoEnabled()) return;
  ensureConfigured();
  await amplifySignOut();
}

