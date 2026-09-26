// ============================================================
// MindCare — Domain Types / Entities
// ============================================================

export type UserRole = 'client' | 'clinician';

export interface NavItem {
  label: string;
  href: string;
}

export interface Stat {
  value: string;
  label: string;
}

// Public, aggregate-only platform counts (GET /stats/public/)
export interface PlatformStats {
  people_in_care: number;
  verified_therapists: number;
  cities: number;
}

export type FeatureIcon = 'therapist' | 'aida' | 'mindband' | 'journal' | 'circles' | 'sos';

export interface Feature {
  id: string;
  icon: FeatureIcon;
  title: string;
  description: string;
  color: string;
}

export interface HowItWorksStep {
  number: string;
  title: string;
  description: string;
}

export interface Partner {
  name: string;
}

// ——— Team / partners section — photoUrl is loaded from the backend ———
export interface TeamMember {
  id: string;
  name: string;
  role: string;
  photoUrl?: string;
}

export interface Therapist {
  id: string;
  name: string;
  specialty: string;
  nextSession: string;
}

export interface MoodEntry {
  day: string;
  value: number;
}

export interface OnboardingChoice {
  role: UserRole;
  selectedAt: string;
}

export interface AppDownloadInfo {
  platform: 'ios' | 'android';
  url: string;
}

// ——— Form / Auth types (ready for backend integration) ———

export interface SignInPayload {
  email: string;
  password: string;
}

export interface SignUpPayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

// ——— Stories page ———
export interface StoryEntry {
  id: string;
  quote: string;
  name: string;
  age: number | null;
  location: string;
  tag: string;
  avatarInitials: string;
  avatarColor: string;
  /** Submitted by this visitor and still awaiting moderation. */
  pending?: boolean;
}

export interface StorySubmission {
  name: string;
  age: number | null;
  location: string;
  tag: string;
  quote: string;
}

// ——— Contact ———
export interface ContactMessage {
  name: string;
  email: string;
  topic: string;
  message: string;
}

// ——— For NGOs page ———
export interface NGOPartnerEntry {
  id: string;
  initials: string;
  color: string;
  name: string;
  description: string;
  routedCount: number;
}

export interface NGORegisterPayload {
  organisationName: string;
  coverageType: string;
  coverage: string;
  contactEmail: string;
  description: string;
}

// ——— For Therapists page ———
export interface TherapistFeature {
  id: string;
  icon: 'code' | 'calendar' | 'file-text' | 'heart' | 'shield';
  title: string;
  description: string;
  color: string;
}

// ——— Therapist onboarding / auth ———
export interface TherapistLoginPayload {
  identifier: string;
  password: string;
  keepSignedIn: boolean;
}

export type TherapistRegisterStep = 'identity' | 'credentials' | 'practice' | 'review';

export interface TherapistCredentials {
  pmdcLicenseNumber: string;
  pmdcVerified: boolean;
  specialty: string;
  degree: string;
  university: string;
  graduationYear: string;
  focusAreas: string[];
  consentBackgroundCheck: boolean;
}

// ——— About Us page ———
export interface AboutValueCard {
  id: string;
  title: string;
  description: string;
}

export interface AboutTimelineEntry {
  id: string;
  date: string;
  description: string;
  current?: boolean;
}

// ——— Help page ———
export interface HelpTopQuestion {
  id: string;
  question: string;
  /** Paragraphs shown when the question is expanded */
  answer: string[];
}

// ——— Pricing page ———
export interface PricingFeatureStrip {
  id: string;
  icon: 'heart' | 'shield' | 'code';
  title: string;
  description: string;
}

// ——— Legal pages (Privacy, Terms, HIPAA Alignment, Cookies) ———
export interface LegalSection {
  id: string;
  title: string;
  body: string[];
}
