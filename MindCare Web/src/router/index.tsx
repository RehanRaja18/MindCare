// ============================================================
// MindCare — Application Router
// Uses React Router v6 with lazy-loaded pages (code-splitting)
// ============================================================

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from '../constants';
import { CONSOLE_ROUTES } from '../constants/therapistConsole';
import { ADMIN_ROUTES } from '../constants/adminConsole';
import { RequireTherapistAuth } from '../utils/authGuard';
import { RequireAdminAuth } from '../utils/adminAuthGuard';
import { AuthProvider } from '../utils/auth';
import ScrollManager from './ScrollManager';

const LandingPage = lazy(() => import('../pages/LandingPage'));
const ClientAppPage = lazy(() => import('../pages/ClientAppPage'));
const StoriesPage = lazy(() => import('../pages/StoriesPage'));
const ForNGOsPage = lazy(() => import('../pages/ForNGOsPage'));
const ForTherapistsPage = lazy(() => import('../pages/ForTherapistsPage'));
const TherapistLoginPage = lazy(() => import('../pages/TherapistLoginPage'));
const TherapistRegisterPage = lazy(() => import('../pages/TherapistRegisterPage'));
const AboutUsPage = lazy(() => import('../pages/AboutUsPage'));
const HelpPage = lazy(() => import('../pages/HelpPage'));
const PricingPage = lazy(() => import('../pages/PricingPage'));
const PrivacyPolicyPage = lazy(() => import('../pages/PrivacyPolicyPage'));
const TermsOfServicePage = lazy(() => import('../pages/TermsOfServicePage'));
const HipaaAlignmentPage = lazy(() => import('../pages/HipaaAlignmentPage'));
const CookiePolicyPage = lazy(() => import('../pages/CookiePolicyPage'));
const TherapistTodayPage = lazy(() => import('../pages/TherapistTodayPage'));
const TherapistPatientsPage = lazy(() => import('../pages/TherapistPatientsPage'));
const PatientDetailPage = lazy(() => import('../pages/PatientDetailPage'));
const TherapistSchedulePage = lazy(() => import('../pages/TherapistSchedulePage'));
const TherapistRequestsPage = lazy(() => import('../pages/TherapistRequestsPage'));
const InSessionPage = lazy(() => import('../pages/InSessionPage'));
const CarePlanEditorPage = lazy(() => import('../pages/CarePlanEditorPage'));
const MessagesPage = lazy(() => import('../pages/MessagesPage'));
const WeeklyReportPage = lazy(() => import('../pages/WeeklyReportPage'));
const ProfilePage = lazy(() => import('../pages/ProfilePage'));
const CirclesPage = lazy(() => import('../pages/CirclesPage'));
const AdminLoginPage = lazy(() => import('../pages/AdminLoginPage'));
const AdminOverviewPage = lazy(() => import('../pages/AdminOverviewPage'));
const AdminVerificationsPage = lazy(() => import('../pages/AdminVerificationsPage'));
const AdminUsersPage = lazy(() => import('../pages/AdminUsersPage'));
const ModerationPage = lazy(() => import('../pages/ModerationPage'));
const SafetyPage = lazy(() => import('../pages/SafetyPage'));
const TherapistsPage = lazy(() => import('../pages/TherapistsPage'));
const NgoPartnersPage = lazy(() => import('../pages/NgoPartnersPage'));
const BillingPage = lazy(() => import('../pages/BillingPage'));
const SettingsPage = lazy(() => import('../pages/SettingsPage'));

const PageLoader: React.FC = () => (
  <div className="min-h-screen bg-[#F5F0E8] flex items-center justify-center" aria-live="polite" aria-label="Loading page">
    <div className="flex flex-col items-center gap-4">
      <div className="w-8 h-8 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-500 font-medium">Loading…</p>
    </div>
  </div>
);

const AppRouter: React.FC = () => (
  <BrowserRouter>
    <ScrollManager />
    <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path={ROUTES.HOME} element={<LandingPage />} />
            <Route path={ROUTES.CLIENT_APP} element={<ClientAppPage />} />
            <Route path={ROUTES.STORIES} element={<StoriesPage />} />
            <Route path={ROUTES.FOR_NGOS} element={<ForNGOsPage />} />
            <Route path={ROUTES.FOR_THERAPISTS} element={<ForTherapistsPage />} />
            <Route path={ROUTES.THERAPIST_LOGIN} element={<TherapistLoginPage />} />
            <Route path={ROUTES.THERAPIST_REGISTER} element={<TherapistRegisterPage />} />
            <Route path={ROUTES.ABOUT_US} element={<AboutUsPage />} />
            <Route path={ROUTES.HELP} element={<HelpPage />} />
            <Route path={ROUTES.PRICING} element={<PricingPage />} />
            <Route path={ROUTES.PRIVACY} element={<PrivacyPolicyPage />} />
            <Route path={ROUTES.TERMS} element={<TermsOfServicePage />} />
            <Route path={ROUTES.HIPAA} element={<HipaaAlignmentPage />} />
            <Route path={ROUTES.COOKIES} element={<CookiePolicyPage />} />

            <Route path={CONSOLE_ROUTES.TODAY} element={<RequireTherapistAuth><TherapistTodayPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.PATIENTS} element={<RequireTherapistAuth><TherapistPatientsPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.PATIENT_DETAIL} element={<RequireTherapistAuth><PatientDetailPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.SCHEDULE} element={<RequireTherapistAuth><TherapistSchedulePage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.REQUESTS} element={<RequireTherapistAuth><TherapistRequestsPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.IN_SESSION} element={<RequireTherapistAuth><InSessionPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.CARE_PLAN} element={<RequireTherapistAuth><CarePlanEditorPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.MESSAGES} element={<RequireTherapistAuth><MessagesPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.WEEKLY_REPORT} element={<RequireTherapistAuth><WeeklyReportPage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.PROFILE} element={<RequireTherapistAuth><ProfilePage /></RequireTherapistAuth>} />
            <Route path={CONSOLE_ROUTES.CIRCLES} element={<RequireTherapistAuth><CirclesPage /></RequireTherapistAuth>} />

            <Route path={ADMIN_ROUTES.SIGN_IN} element={<AdminLoginPage />} />
            <Route path={ADMIN_ROUTES.OVERVIEW} element={<RequireAdminAuth><AdminOverviewPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.VERIFICATIONS} element={<RequireAdminAuth><AdminVerificationsPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.USERS} element={<RequireAdminAuth><AdminUsersPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.MODERATION} element={<RequireAdminAuth><ModerationPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.SAFETY} element={<RequireAdminAuth><SafetyPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.THERAPISTS} element={<RequireAdminAuth><TherapistsPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.NGO_PARTNERS} element={<RequireAdminAuth><NgoPartnersPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.BILLING} element={<RequireAdminAuth><BillingPage /></RequireAdminAuth>} />
            <Route path={ADMIN_ROUTES.SETTINGS} element={<RequireAdminAuth><SettingsPage /></RequireAdminAuth>} />

            <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
          </Routes>
        </Suspense>
      </AuthProvider>
  </BrowserRouter>
);

export default AppRouter;