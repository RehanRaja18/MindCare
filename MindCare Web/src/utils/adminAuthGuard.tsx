// ============================================================
// MindCare — Admin Console Auth Guard
// Reads the real session (see utils/auth.tsx). Only accounts whose
// token role is "admin" can enter the admin console. Admin sessions
// never persist past the browser tab.
//
// Still to do server-side before this console handles real data:
// MFA for admin sign-in, fine-grained admin permissions (not one
// "is admin" flag), and audit logging of every sensitive action.
// ============================================================

import React, { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { ADMIN_ROUTES } from '../constants/adminConsole';
import { useAuth } from './auth';

interface AdminSession {
  id: string;
  name: string;
  initials: string;
  role: string;
}

export const useAdminAuth = () => {
  const { session, signOut } = useAuth();
  const admin: AdminSession | null =
    session?.role === 'admin'
      ? { id: session.userId, name: session.name, initials: session.initials, role: 'Admin' }
      : null;
  return { admin, isAuthenticated: !!admin, logout: signOut };
};

/** Route guard — redirects to admin sign-in unless signed in as an admin. */
export const RequireAdminAuth: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAdminAuth();
  if (!isAuthenticated) {
    return <Navigate to={ADMIN_ROUTES.SIGN_IN} replace />;
  }
  return <>{children}</>;
};
