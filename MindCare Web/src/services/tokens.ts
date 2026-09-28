// ============================================================
// MindCare — Auth token storage
// Holds the JWT pair issued by POST /accounts/login/ and reads the
// claims the backend puts in the access token (user_id, role, exp).
//
// The backend returns the tokens in the JSON body (no httpOnly cookie),
// so they have to live in web storage. "Keep me signed in" uses
// localStorage (survives closing the browser); otherwise sessionStorage
// (cleared when the tab closes). Admin sign-in never persists.
// ============================================================

export type Role = 'patient' | 'psychologist' | 'admin' | 'ngo';

export interface TokenClaims {
  userId: string;
  role: Role;
  /** Expiry, in seconds since epoch */
  exp: number;
}

const ACCESS_KEY = 'mc_access_token';
const REFRESH_KEY = 'mc_refresh_token';
const EMAIL_KEY = 'mc_session_email';

const stores = (): Storage[] => {
  try {
    return [window.sessionStorage, window.localStorage];
  } catch {
    return []; // storage blocked (e.g. privacy mode) — act signed out
  }
};

const read = (key: string): string | null => {
  for (const s of stores()) {
    try {
      const v = s.getItem(key);
      if (v) return v;
    } catch {
      /* ignore */
    }
  }
  return null;
};

/** Which store the current session lives in (so refreshes stay put). */
const activeStore = (): Storage | null => stores().find((s) => {
  try {
    return !!s.getItem(REFRESH_KEY);
  } catch {
    return false;
  }
}) ?? null;

export function saveTokens(access: string, refresh: string, opts?: { remember?: boolean; email?: string }) {
  const all = stores();
  const target = opts?.remember === undefined ? activeStore() ?? all[0] : opts.remember ? all[1] : all[0];
  if (!target) return;
  if (opts?.remember !== undefined) clearTokens(); // new sign-in: don't leave a copy in the other store
  try {
    target.setItem(ACCESS_KEY, access);
    target.setItem(REFRESH_KEY, refresh);
    if (opts?.email) target.setItem(EMAIL_KEY, opts.email);
  } catch {
    /* storage full / blocked */
  }
}

export function clearTokens() {
  for (const s of stores()) {
    try {
      s.removeItem(ACCESS_KEY);
      s.removeItem(REFRESH_KEY);
      s.removeItem(EMAIL_KEY);
    } catch {
      /* ignore */
    }
  }
}

export const getAccessToken = () => read(ACCESS_KEY);
export const getRefreshToken = () => read(REFRESH_KEY);
export const getSessionEmail = () => read(EMAIL_KEY);

/** Decode a JWT's payload without verifying it — the server verifies; we only read claims. */
export function decodeClaims(token: string | null): TokenClaims | null {
  if (!token) return null;
  try {
    const part = token.split('.')[1];
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '='));
    const p = JSON.parse(json) as { user_id?: unknown; role?: unknown; exp?: unknown };
    const roles: Role[] = ['patient', 'psychologist', 'admin', 'ngo'];
    if (!roles.includes(p.role as Role) || typeof p.exp !== 'number') return null;
    return { userId: String(p.user_id ?? ''), role: p.role as Role, exp: p.exp };
  } catch {
    return null;
  }
}

/** True if the token expires within `skewSeconds` (or can't be read). */
export function isExpired(token: string | null, skewSeconds = 30): boolean {
  const claims = decodeClaims(token) ?? (token ? decodeExpOnly(token) : null);
  return !claims || claims.exp * 1000 <= Date.now() + skewSeconds * 1000;
}

// Refresh tokens carry no "role" claim, so read just their expiry.
function decodeExpOnly(token: string): { exp: number } | null {
  try {
    const part = token.split('.')[1];
    const p = JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '=')));
    return typeof p.exp === 'number' ? { exp: p.exp } : null;
  } catch {
    return null;
  }
}
