/**
 * API configuration from environment.
 * Vite exposes env vars prefixed with VITE_ via import.meta.env.
 */
const VITE_API_URL = import.meta.env.VITE_API_URL ?? '';
const VITE_USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || import.meta.env.VITE_USE_MOCK === '1';
const VITE_COGNITO_USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID ?? '';
const VITE_COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID ?? '';
const VITE_COGNITO_REGION = import.meta.env.VITE_COGNITO_REGION ?? 'ap-south-1';

export const config = {
  apiUrl: VITE_API_URL?.replace(/\/$/, '') || '',
  useMock: VITE_USE_MOCK,
  cognito: {
    userPoolId: VITE_COGNITO_USER_POOL_ID,
    clientId: VITE_COGNITO_CLIENT_ID,
    region: VITE_COGNITO_REGION,
  },
};

export function isCognitoEnabled() {
  return !!(config.cognito.userPoolId && config.cognito.clientId);
}

export function isMockMode() {
  return config.useMock || !config.apiUrl;
}

