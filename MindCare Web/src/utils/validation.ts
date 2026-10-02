// ============================================================
// MindCare — Input Validation & Sanitization Utilities
//
// IMPORTANT: These are FRONTEND UX safeguards only. They catch
// mistakes early and reduce garbage data, but they are NOT a
// security boundary — anyone can bypass client-side JS entirely.
// The backend MUST independently re-validate everything here
// (parameterized queries, server-side length/format checks,
// rate limiting, auth, HTTPS) before trusting any of this data.
//
// PASSWORD POLICY NOTE (updated to current industry guidance):
// Following NIST 800-63B and common 2025/2026 industry practice,
// this favors LENGTH over rigid composition rules, and a real
// backend must additionally:
//   - Check new passwords against a breached-password list
//     (e.g. the HaveIBeenPwned k-anonymity range API) and reject
//     matches, rather than relying on composition rules alone.
//   - Hash with a slow, salted algorithm (argon2id or bcrypt),
//     never store or log plaintext passwords.
//   - Rate-limit and lock out repeated failed attempts server-side
//     — the client-side attempt counters in this app are UX only
//     and are trivially bypassed by anyone calling the API directly.
//   - Require MFA for any account with elevated access (therapist,
//     admin) — see src/utils/adminAuthGuard.tsx.
// ============================================================

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// Reasonable max lengths — prevents accidental huge payloads
// and basic denial-of-service-by-textarea abuse.
export const MAX_LENGTHS = {
  shortText: 100, // names, titles
  email: 254, // RFC 5321 limit
  longText: 1000, // paragraphs / descriptions
  password: 128,
} as const;

// Minimum password length. NIST 800-63B sets 8 as an absolute floor
// but recommends encouraging longer passphrases; most 2025/2026
// consumer platforms (Google, Microsoft, Apple) require 10-12+.
export const MIN_PASSWORD_LENGTH = 12;

/**
 * Validates email format. Returns null if valid, or an error message.
 */
export function validateEmail(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Email is required.';
  if (trimmed.length > MAX_LENGTHS.email) return 'Email is too long.';
  if (!EMAIL_REGEX.test(trimmed)) return 'Enter a valid email address.';
  return null;
}

/**
 * Validates a required short text field (names, titles, etc.)
 */
export function validateRequiredText(value: string, label: string, maxLength: number = MAX_LENGTHS.shortText): string | null {
  const trimmed = value.trim();
  if (!trimmed) return `${label} is required.`;
  if (trimmed.length > maxLength) return `${label} must be under ${maxLength} characters.`;
  return null;
}

/**
 * Strips characters with no legitimate use in plain-text form fields
 * (angle brackets) to reduce accidental markup/script injection surface.
 * NOTE: React already escapes rendered text by default — this is a
 * defence-in-depth measure for data that may later be sent elsewhere
 * (emails, admin dashboards, exports) that might not escape it.
 */
export function sanitizeText(value: string): string {
  return value.replace(/[<>]/g, '').trim();
}

/**
 * Validates a PMDC license number format (e.g. "102-CP-44871").
 * Real verification against PMDC.gov.pk must happen server-side —
 * this only rejects obviously malformed input.
 */
const PMDC_ID_REGEX = /^[A-Za-z0-9]{2,6}-[A-Za-z0-9]{1,8}-[A-Za-z0-9]{1,10}$/;

export function validatePmdcLicense(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'PMDC license number is required.';
  if (!PMDC_ID_REGEX.test(trimmed)) {
    return 'Enter a valid PMDC license number (e.g. 102-CP-44871).';
  }
  return null;
}

/**
 * For fields that accept either an email or a PMDC ID (e.g. therapist
 * sign-in "Email or PMDC ID"). Detects which format was entered and
 * validates accordingly.
 */
export function validateEmailOrPmdcId(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Email or PMDC ID is required.';
  if (trimmed.includes('@')) {
    return validateEmail(trimmed);
  }
  return validatePmdcLicense(trimmed);
}

/**
 * Password policy for NEW passwords (signup/registration/change).
 * Length-first, per current guidance — still asks for a mix of
 * character types since that remains a reasonable, low-friction
 * floor, but the primary bar is length.
 */
export function validatePassword(value: string): string | null {
  if (!value) return 'Password is required.';
  if (value.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (value.length > MAX_LENGTHS.password) return 'Password is too long.';
  if (!/[a-z]/.test(value) || !/[A-Z]/.test(value)) {
    return 'Password must include both uppercase and lowercase letters.';
  }
  if (!/[0-9]/.test(value)) {
    return 'Password must include at least one number.';
  }
  return null;
}

/**
 * Lighter check for SIGN-IN (not signup). Existing accounts may
 * predate a policy change, so sign-in should only reject passwords
 * that are clearly too short to be valid, and let the real auth
 * check (server-side) be the source of truth for correctness.
 */
export function validatePasswordForSignIn(value: string): string | null {
  if (!value) return 'Password is required.';
  if (value.length < 8) return 'Password must be at least 8 characters.';
  if (value.length > MAX_LENGTHS.password) return 'Password is too long.';
  return null;
}

/**
 * Confirms two password fields match. Use alongside validatePassword
 * on every signup/registration/change-password form.
 */
export function validatePasswordConfirmation(password: string, confirmation: string): string | null {
  if (!confirmation) return 'Please confirm your password.';
  if (password !== confirmation) return 'Passwords do not match.';
  return null;
}

export type PasswordStrengthLabel = 'Too short' | 'Weak' | 'Fair' | 'Good' | 'Strong';

export interface PasswordStrength {
  score: 0 | 1 | 2 | 3 | 4;
  label: PasswordStrengthLabel;
  color: string;
}

/**
 * Rough client-side strength estimate for live UI feedback only
 * (a progress-bar style meter). This is NOT a substitute for
 * server-side breach-list checking — a password can score "Strong"
 * here and still be a known-leaked password.
 */
export function getPasswordStrength(value: string): PasswordStrength {
  if (!value || value.length < MIN_PASSWORD_LENGTH) {
    return { score: 0, label: 'Too short', color: '#d1d5db' };
  }

  let score = 0;
  if (value.length >= MIN_PASSWORD_LENGTH) score += 1;
  if (value.length >= 16) score += 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
  if (/[0-9]/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;

  const clamped = Math.min(4, Math.max(0, score - 1)) as 0 | 1 | 2 | 3 | 4;

  const levels: Record<0 | 1 | 2 | 3 | 4, { label: PasswordStrengthLabel; color: string }> = {
    0: { label: 'Weak', color: '#dc2626' },
    1: { label: 'Weak', color: '#dc2626' },
    2: { label: 'Fair', color: '#d97706' },
    3: { label: 'Good', color: '#65a30d' },
    4: { label: 'Strong', color: '#15803d' },
  };

  return { score: clamped, ...levels[clamped] };
}