// ============================================================
// MindCare — Session (real backend auth)
// One session for the whole web app, backed by the JWT pair from
// POST /accounts/login/. The "role" claim in the access token decides
// which console the user may enter:
//   admin → admin console · psychologist → therapist console.
// Patients use the mobile app and NGOs have no web console yet, so
// those roles are signed straight back out with an explanation.
//
// The console guards are a UI convenience only — every API call is
// authorised server-side by the backend from the token itself.
// ============================================================

import React, { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { login as loginRequest, logoutRequest, refreshTokens } from '../services/api.service';
import {
  clearTokens,
  decodeClaims,
  getAccessToken,
  getRefreshToken,
  getSessionEmail,
  isExpired,
  saveTokens,
  type Role,
} from '../services/tokens';
import { ADMIN_ROUTES } from '../constants/adminConsole';
import { CONSOLE_ROUTES } from '../constants/therapistConsole';

export interface Session {
  userId: string;
  role: Role;
  email: string;
  /** Display name — the backend token has no name, so derived from the email */
  name: string;
  initials: string;
}

export type SignInResult = { ok: true; session: Session } | { ok: false; error: string };

interface AuthContextValue {
  session: Session | null;
  signIn: (email: string, password: string, opts?: { remember?: boolean }) => Promise<SignInResult>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  session: null,
  signIn: async () => ({ ok: false, error: 'Not ready' }),
  signOut: () => {},
});

export const useAuth = () => useContext(AuthContext);

const WEB_ROLES: Role[] = ['admin', 'psychologist'];

const ROLE_NOT_ON_WEB: Partial<Record<Role, string>> = {
  patient: 'Patient accounts use the MindCare mobile app. Download it from the Get started page and sign in there.',
  ngo: 'NGO accounts don’t have a web dashboard yet. Please contact the MindCare team.',
};

function nameFromEmail(email: string) {
  const local = email.split('@')[0] ?? '';
  const words = local.split(/[._-]+/).filter(Boolean);
  const name = words.map((w) => w[0].toUpperCase() + w.slice(1)).join(' ') || email;
  const initials = (words.length > 1 ? words[0][0] + words[1][0] : local.slice(0, 2)).toUpperCase();
  return { name, initials };
}

/** Build the session from stored tokens, if the refresh token is still valid. */
function readSession(): Session | null {
  const refresh = getRefreshToken();
  if (!refresh || isExpired(refresh, 0)) return null;
  const claims = decodeClaims(getAccessToken()) ?? decodeClaims(refresh);
  if (!claims || !WEB_ROLES.includes(claims.role)) return null;
  const email = getSessionEmail() ?? '';
  return { userId: claims.userId, role: claims.role, email, ...nameFromEmail(email) };
}

/** Where each role lands after signing in. */
export const homeForRole = (role: Role) => (role === 'admin' ? ADMIN_ROUTES.OVERVIEW : CONSOLE_ROUTES.TODAY);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(readSession);

  // Drop a session whose refresh token has expired or been revoked.
  useEffect(() => {
    if (!session || !isExpired(getAccessToken())) return;
    refreshTokens().then((ok) => {
      if (!ok) {
        clearTokens();
        setSession(null);
      }
    });
  }, [session]);

  const signIn = useCallback<AuthContextValue['signIn']>(async (email, password, opts) => {
    const res = await loginRequest(email, password);
    if (!res.data) {
      // Shown as-is: wrong credentials, "pending admin approval", rate limit…
      return { ok: false, error: res.error ?? 'Sign-in failed. Please try again.' };
    }

    const claims = decodeClaims(res.data.access);
    if (!claims) return { ok: false, error: 'Signed in, but the account role couldn’t be read. Please contact support.' };
    if (!WEB_ROLES.includes(claims.role)) {
      return { ok: false, error: ROLE_NOT_ON_WEB[claims.role] ?? 'This account can’t use the web dashboard.' };
    }

    saveTokens(res.data.access, res.data.refresh, {
      remember: claims.role === 'admin' ? false : !!opts?.remember,
      email,
    });
    const next = readSession();
    if (!next) return { ok: false, error: 'Sign-in failed. Please try again.' };
    setSession(next);
    return { ok: true, session: next };
  }, []);

  const signOut = useCallback(() => {
    logoutRequest().finally(clearTokens); // tell the backend, but never block the user
    setSession(null);
  }, []);

  return <AuthContext.Provider value={{ session, signIn, signOut }}>{children}</AuthContext.Provider>;
};
