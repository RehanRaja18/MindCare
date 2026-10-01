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

// ——— POST /accounts/register/ (backend contract) ———
// JSON only. Unknown fields anywhere are rejected with a 400, so these
// types list exactly what the backend accepts — nothing more.

export interface PatientProfile {
  timezone: string;
}

export interface PsychologistProfile {
  license_number: string;
  license_issuing_country: string; // ISO 3166-1 alpha-2, e.g. "PK"
  license_issuing_authority: string;
  qualifications: string;
  specializations: string[];
  years_of_experience: number;
  languages: string[]; // ISO 639-1, e.g. "en", "ur"
  country: string;
  city: string;
  timezone: string; // IANA, e.g. "Asia/Karachi"
  /** Optional: "male" | "female" | "other" | "prefer_not_to_say" | null */
  gender?: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null;
  /** Optional, max 2000 */
  bio?: string;
}

export interface NgoServiceArea {
  country: string;
  city?: string;
}

export interface NgoProfile {
  organization_name: string;
  registration_number: string;
  registration_country: string;
  registering_authority: string;
  country: string;
  city: string;
  timezone: string;
  /** E.164, e.g. "+922111234567" */
  official_phone: string;
  official_email: string;
  /** Optional */
  website?: string;
  /** Optional, max 2000 */
  description?: string;
  service_areas: NgoServiceArea[];
}

interface RegisterBase {
  email: string;
  password: string;
  full_name: string;
  /** Must be the JSON boolean true — the backend rejects "true" or 1. */
  is_adult_confirmed: true;
}

export type RegisterPayload =
  | (RegisterBase & { role: 'patient'; profile: PatientProfile })
  | (RegisterBase & { role: 'psychologist'; profile: PsychologistProfile })
  | (RegisterBase & { role: 'ngo'; profile: NgoProfile });

/** 201 body. No tokens — sign in afterwards. Psychologist/NGO start "pending". */
export interface RegisteredUser {
  approval_status?: 'approved' | 'pending' | 'rejected';
  [key: string]: unknown;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  /** HTTP status (0 = network failure); absent on local stubs */
  status?: number;
  /** Raw error body (e.g. DRF field errors, nested under "profile") */
  errorBody?: unknown;
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
export interface HelpGuideStep {
  id: string;
  title: string;
  /** Where this step happens */
  where: 'Mobile app' | 'Website' | 'Email';
  body: string;
  /** Optional in-site link for the step, e.g. the apply form */
  link?: { label: string; to: string };
}

export interface HelpGuide {
  id: 'patient' | 'psychologist';
  tab: string;
  intro: string;
  steps: HelpGuideStep[];
}

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
