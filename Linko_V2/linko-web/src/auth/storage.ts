import type { AuthUser } from './types';

const KEY = 'linko-auth';

export function loadAuth(): AuthUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const u = JSON.parse(raw) as AuthUser;
    if (!u?.token || !u?.role || !u?.username) return null;
    if (u.expires_at != null && Date.now() >= u.expires_at) {
      localStorage.removeItem(KEY);
      return null;
    }
    return u;
  } catch {
    return null;
  }
}

export function saveAuth(user: AuthUser) {
  localStorage.setItem(KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(KEY);
}
