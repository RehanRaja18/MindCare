// ============================================================
// MindCare — Therapist Console Auth Guard
// Reads the real session (see utils/auth.tsx). Only accounts whose
// token role is "psychologist" can enter the therapist console.
// This guard is UI only — the backend authorises every API call
// and must keep enforcing that a psychologist only sees their own
// patients (row-level checks), regardless of what the UI shows.
// ============================================================

import React, { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { ROUTES } from '../constants';
import { useAuth } from './auth';

interface TherapistSession {
  id: string;
  name: string;
  initials: string;
  license: string;
}

export const useTherapistAuth = () => {
  const { session, signOut } = useAuth();
  const therapist: TherapistSession | null =
    session?.role === 'psychologist'
      ? { id: session.userId, name: session.name, initials: session.initials, license: 'PMDC' }
      : null;
  return { therapist, isAuthenticated: !!therapist, logout: signOut };
};

/** Route guard — redirects to therapist sign-in unless signed in as a psychologist. */
export const RequireTherapistAuth: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useTherapistAuth();
  if (!isAuthenticated) {
    return <Navigate to={ROUTES.THERAPIST_LOGIN} replace />;
  }
  return <>{children}</>;
};
