/**
 * Cognito auth helper. Only used when VITE_COGNITO_USER_POOL_ID and VITE_COGNITO_CLIENT_ID are set.
 * Uses AWS Amplify Auth; role can be read from custom:role attribute or token.
 */
import { Amplify } from 'aws-amplify';
import { signIn, getCurrentUser, signOut as amplifySignOut } from 'aws-amplify/auth';
import { fetchAuthSession } from 'aws-amplify/auth';
import { config, isCognitoEnabled } from '../api/config';

let configured = false;

/** Derive a display name from email or username (e.g. doc1@cdss.ai → Doc1, priya.sharma@... → Priya Sharma). */
function displayNameFromEmailOrUsername(emailOrUsername) {
  if (!emailOrUsername || typeof emailOrUsername !== 'string') return '';
  const local = emailOrUsername.includes('@') ? emailOrUsername.split('@')[0] : emailOrUsername;
  const words = local.replace(/[._-]+/g, ' ').trim().split(/\s+/);
  return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ') || local;
}

function getDisplayName(payload, fallbackEmailOrUsername) {
  if (payload.name && typeof payload.name === 'string' && payload.name.trim()) return payload.name.trim();
  const given = payload.given_name;
  const family = payload.family_name;
  if (given && family) return `${given} ${family}`.trim();
  if (given) return given;
  if (payload.preferred_username && typeof payload.preferred_username === 'string') return payload.preferred_username.trim();
  return displayNameFromEmailOrUsername(payload.email || fallbackEmailOrUsername);
}

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
  const role = payload['custom:role'] || payload.role || 'doctor';
  const name = getDisplayName(payload, email);
  return {
    id: payload.sub || email,
    name,
    email,
    role: role.toLowerCase(),
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
    const role = payload['custom:role'] || payload.role || 'doctor';
    const email = payload.email || user?.signInDetails?.loginId || '';
    return {
      id: payload.sub || user?.userId,
      name: getDisplayName(payload, email || user?.username),
      email,
      role: role.toLowerCase(),
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
