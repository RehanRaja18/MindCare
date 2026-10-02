// ============================================================
// MindCare — Therapist Registration Wizard ("Let's get you verified.")
// Submits POST /accounts/register/ with role "psychologist" and the
// nested profile the backend expects. The account starts "pending"
// until an admin approves it; only then can the therapist sign in.
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ArrowRight, ArrowLeft, Eye, EyeOff, CheckCircle2, Pencil } from 'lucide-react';
import Button from '../components/common/Button';
import PasswordStrengthMeter from '../components/common/PasswordStrengthMeter';
import { AdultConfirm, ChipGroup, SelectField, TextAreaField, TextField } from '../components/forms/Fields';
import {
  ROUTES,
  THERAPIST_ONBOARDING_STEPS,
  THERAPIST_WHAT_HAPPENS_NEXT,
  THERAPIST_STATS,
} from '../constants';
import { register, flattenFieldErrors } from '../services/api.service';
import {
  validateRequiredText,
  validateEmail,
  validatePassword,
  validatePasswordConfirmation,
  sanitizeText,
  MAX_LENGTHS,
} from '../utils/validation';
import {
  COMMON_LANGUAGE_CODES,
  COUNTRY_OPTIONS,
  DEFAULT_TIMEZONE,
  LANGUAGE_OPTIONS,
  SPECIALIZATION_FALLBACK,
  TIMEZONE_OPTIONS,
  sortCountries,
  type Option,
} from '../utils/locale';
import { useReferenceOptions } from '../hooks/useReferenceOptions';
import type { PsychologistProfile, RegisterPayload, TherapistRegisterStep } from '../types';

const MIN_SPECIALIZATIONS = 1;
const MAX_SPECIALIZATIONS = 6;


// Backend choices (core.choices.Gender); optional — empty is sent as null.
const GENDER_OPTIONS: Option[] = [
  { value: '', label: 'Not specified' },
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

// Backend field limits (PsychologistRegistrationProfileSerializer)
const LIMITS = { license: 64, authority: 200, qualifications: 1000, city: 120, bio: 2000 };

interface FormState {
  full_name: string;
  email: string;
  password: string;
  confirm: string;
  adult: boolean;
  license_number: string;
  license_issuing_country: string;
  license_issuing_authority: string;
  degree: string;
  university: string;
  graduation_year: string;
  specializations: string[];
  consent: boolean;
  years_of_experience: string;
  languages: string[];
  country: string;
  city: string;
  timezone: string;
  gender: string;
  bio: string;
}

const initialForm: FormState = {
  full_name: '',
  email: '',
  password: '',
  confirm: '',
  adult: false,
  license_number: '',
  license_issuing_country: 'PK',
  license_issuing_authority: 'Pakistan Medical and Dental Council',
  degree: '',
  university: '',
  graduation_year: '',
  specializations: [],
  consent: false,
  years_of_experience: '',
  languages: [],
  country: 'PK',
  city: '',
  timezone: DEFAULT_TIMEZONE,
  gender: '',
  bio: '',
};

type Errors = Record<string, string | undefined>;

// Which step each error key belongs to (contract paths + client-only keys),
// so a 400 from the backend takes the user straight to the right step.
const STEP_OF: Record<string, TherapistRegisterStep> = {
  full_name: 'identity',
  email: 'identity',
  password: 'identity',
  confirm: 'identity',
  is_adult_confirmed: 'identity',
  role: 'identity',
  'profile.license_number': 'credentials',
  'profile.license_issuing_country': 'credentials',
  'profile.license_issuing_authority': 'credentials',
  'profile.qualifications': 'credentials',
  degree: 'credentials',
  'profile.specializations': 'credentials',
  consent: 'credentials',
  'profile.years_of_experience': 'practice',
  'profile.languages': 'practice',
  'profile.country': 'practice',
  'profile.city': 'practice',
  'profile.timezone': 'practice',
  'profile.gender': 'practice',
  'profile.bio': 'practice',
};

const STEP_ORDER: TherapistRegisterStep[] = ['identity', 'credentials', 'practice', 'review'];

const qualificationsOf = (f: FormState) =>
  [sanitizeText(f.degree), sanitizeText(f.university), f.graduation_year.trim()].filter(Boolean).join(', ');

const TherapistRegisterPage: React.FC = () => {
  const [activeStep, setActiveStep] = useState<TherapistRegisterStep>('identity');
  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<{ pending: boolean } | null>(null);

  const stepIndex = STEP_ORDER.indexOf(activeStep);

  // Live reference lists (the API only accepts values from these)
  const { options: SPECIALIZATION_OPTIONS } = useReferenceOptions('specializations', SPECIALIZATION_FALLBACK);
  const { options: allLanguages } = useReferenceOptions('languages', LANGUAGE_OPTIONS);
  const { options: countries } = useReferenceOptions('countries', COUNTRY_OPTIONS, sortCountries);
  const commonLanguages = COMMON_LANGUAGE_CODES.map((c) => allLanguages.find((l) => l.value === c)).filter(Boolean) as Option[];
  // Quick-pick chips: common languages plus any other language already chosen
  const languageChips = [
    ...commonLanguages,
    ...form.languages
      .filter((c) => !COMMON_LANGUAGE_CODES.includes(c))
      .map((c) => allLanguages.find((l) => l.value === c) ?? { value: c, label: c }),
  ];
  const otherLanguages = allLanguages.filter((l) => !languageChips.some((c) => c.value === l.value));

  const set = <K extends keyof FormState>(key: K, value: FormState[K], errorKey: string = key) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[errorKey]) setErrors((prev) => ({ ...prev, [errorKey]: undefined }));
  };
  const setProfile = <K extends keyof FormState>(key: K) => (value: FormState[K]) => set(key, value, `profile.${key}`);

  // Functional update, so quick successive taps never overwrite each other.
  const toggle = (key: 'specializations' | 'languages', value: string, max = Infinity) => {
    setForm((prev) => {
      const list = prev[key];
      const next = list.includes(value) ? list.filter((v) => v !== value) : list.length >= max ? list : [...list, value];
      return { ...prev, [key]: next };
    });
    if (errors[`profile.${key}`]) setErrors((prev) => ({ ...prev, [`profile.${key}`]: undefined }));
  };

  const goToStep = (step: TherapistRegisterStep) => {
    setActiveStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ——— Client-side checks per step (the backend re-validates everything) ———
  const checkIdentity = (): Errors => ({
    full_name: validateRequiredText(form.full_name, 'Full name') ?? undefined,
    email: validateEmail(form.email) ?? undefined,
    password: validatePassword(form.password) ?? undefined,
    confirm: validatePasswordConfirmation(form.password, form.confirm) ?? undefined,
    is_adult_confirmed: form.adult ? undefined : 'You must be 18 or older to join MindCare.',
  });

  const checkCredentials = (): Errors => ({
    'profile.license_number': validateRequiredText(form.license_number, 'Licence number', LIMITS.license) ?? undefined,
    'profile.license_issuing_country': form.license_issuing_country ? undefined : 'Choose the issuing country.',
    'profile.license_issuing_authority':
      validateRequiredText(form.license_issuing_authority, 'Issuing authority', LIMITS.authority) ?? undefined,
    degree:
      validateRequiredText(form.degree, 'Degree') ??
      (qualificationsOf(form).length > LIMITS.qualifications ? 'Degree and university are too long.' : undefined),
    'profile.specializations':
      form.specializations.length >= MIN_SPECIALIZATIONS ? undefined : 'Pick at least one area you work with.',
    consent: form.consent ? undefined : 'Please consent to verification to continue.',
  });

  const checkPractice = (): Errors => {
    const years = Number(form.years_of_experience);
    return {
      'profile.years_of_experience':
        form.years_of_experience.trim() === '' || !Number.isInteger(years) || years < 0 || years > 70
          ? 'Enter your years of experience as a whole number.'
          : undefined,
      'profile.languages': form.languages.length ? undefined : 'Pick at least one language.',
      'profile.country': form.country ? undefined : 'Choose your country.',
      'profile.city': validateRequiredText(form.city, 'City', LIMITS.city) ?? undefined,
      'profile.timezone': form.timezone ? undefined : 'Choose your time zone.',
      'profile.bio': form.bio.length > LIMITS.bio ? `Bio must be under ${LIMITS.bio} characters.` : undefined,
    };
  };

  const proceed = (check: () => Errors, next: TherapistRegisterStep) => {
    const found = Object.fromEntries(Object.entries(check()).filter(([, v]) => v)) as Errors;
    setErrors((prev) => ({ ...prev, ...check(), ...found }));
    if (Object.keys(found).length === 0) goToStep(next);
  };

  // ——— Submit ———
  const buildPayload = (): RegisterPayload => {
    const profile: PsychologistProfile = {
      license_number: form.license_number.trim(),
      license_issuing_country: form.license_issuing_country,
      license_issuing_authority: sanitizeText(form.license_issuing_authority),
      qualifications: qualificationsOf(form),
      specializations: form.specializations,
      years_of_experience: Number(form.years_of_experience),
      languages: form.languages,
      country: form.country,
      city: sanitizeText(form.city),
      timezone: form.timezone,
      gender: (form.gender || null) as PsychologistProfile['gender'],
      bio: sanitizeText(form.bio),
    };
    if (!profile.bio) delete (profile as Partial<PsychologistProfile>).bio; // optional
    return {
      email: form.email.trim().toLowerCase(),
      password: form.password,
      full_name: sanitizeText(form.full_name),
      role: 'psychologist',
      is_adult_confirmed: true,
      profile,
    };
  };

  const handleSubmit = async () => {
    const all = { ...checkIdentity(), ...checkCredentials(), ...checkPractice() };
    const firstBad = STEP_ORDER.find((s) => Object.entries(all).some(([k, v]) => v && STEP_OF[k] === s));
    if (firstBad) {
      setErrors(all);
      goToStep(firstBad);
      return;
    }

    setSubmitting(true);
    setFormError(null);
    const res = await register(buildPayload());
    setSubmitting(false);

    if (res.data) {
      setSubmitted({ pending: res.data.approval_status !== 'approved' });
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (res.status === 400 && res.errorBody) {
      const fieldErrors = flattenFieldErrors(res.errorBody);
      // "qualifications" is built from degree/university/year
      if (fieldErrors['profile.qualifications']) fieldErrors.degree = fieldErrors['profile.qualifications'];
      setErrors(fieldErrors);
      const unplaced = Object.entries(fieldErrors).filter(([k]) => !STEP_OF[k]);
      setFormError(
        unplaced.length
          ? unplaced.map(([k, v]) => (k === '_' ? v : `${k.replace(/^profile\./, '')}: ${v}`)).join(' ')
          : 'Please fix the highlighted fields.'
      );
      const step = STEP_ORDER.find((s) => Object.keys(fieldErrors).some((k) => STEP_OF[k] === s));
      if (step) goToStep(step);
      return;
    }
    setFormError(res.error ?? 'Something went wrong. Please try again.'); // e.g. rate limit, offline
  };

  const e = (key: string) => errors[key];

  return (
    <div className="min-h-screen bg-[#F5F0E8]">
      {/* Header */}
      <header className="flex items-center justify-between gap-4 px-4 sm:px-10 py-6">
        <Link to={ROUTES.HOME} className="text-xl font-bold tracking-tight text-gray-900 shrink-0">
          MindCare<span className="text-orange-500">.</span>
        </Link>
        <p className="text-sm text-gray-500 text-right">
          Already a therapist here?{' '}
          <Link to={ROUTES.THERAPIST_LOGIN} className="font-semibold text-gray-900 underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
            Therapist · Apply to practice
          </p>
          <h1 className="text-4xl sm:text-5xl font-black text-gray-900 mb-4">
            Let&apos;s get you <span className="italic font-serif font-normal">verified.</span>
          </h1>
          <p className="text-gray-600 max-w-xl mb-8">
            MindCare only accepts licensed clinicians. After you apply, an admin reviews your details
            before your account is activated.
          </p>

          {submitted ? (
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 sm:p-10 text-center">
              <CheckCircle2 size={48} className="mx-auto text-emerald-500 mb-5" aria-hidden="true" />
              <h2 className="text-2xl sm:text-3xl font-black text-gray-900 mb-3">Application received.</h2>
              {submitted.pending ? (
                <p className="text-gray-600 max-w-md mx-auto mb-8">
                  Your account is <strong>pending admin approval</strong>. You&apos;ll be able to sign in
                  with <strong>{form.email.trim().toLowerCase()}</strong> once an admin has approved it.
                </p>
              ) : (
                <p className="text-gray-600 max-w-md mx-auto mb-8">Your account is ready. You can sign in now.</p>
              )}
              <Link to={ROUTES.THERAPIST_LOGIN}>
                <Button variant="primary" size="md" className="rounded-full">
                  Go to sign in <ArrowRight size={14} />
                </Button>
              </Link>
            </div>
          ) : (
            <>
              {/* Step tracker */}
              <div className="flex items-center gap-2 mb-8">
                {THERAPIST_ONBOARDING_STEPS.map((step, i) => {
                  const isDone = i < stepIndex;
                  const isActive = i === stepIndex;
                  return (
                    <React.Fragment key={step.id}>
                      <button
                        type="button"
                        onClick={() => (isDone ? goToStep(step.id as TherapistRegisterStep) : undefined)}
                        className={`flex items-center gap-2 shrink-0 ${isDone ? 'cursor-pointer' : 'cursor-default'}`}
                      >
                        <span
                          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                            isDone
                              ? 'bg-emerald-600 text-white'
                              : isActive
                              ? 'bg-gray-900 text-white'
                              : 'bg-white border border-gray-300 text-gray-400'
                          }`}
                        >
                          {isDone ? <Check size={14} /> : i + 1}
                        </span>
                        <span
                          className={`text-sm font-semibold ${isActive ? '' : 'hidden sm:inline'} ${
                            isActive || isDone ? 'text-gray-900' : 'text-gray-400'
                          }`}
                        >
                          {step.label}
                        </span>
                      </button>
                      {i < THERAPIST_ONBOARDING_STEPS.length - 1 && (
                        <span className={`flex-1 min-w-3 h-0.5 ${isDone ? 'bg-emerald-600' : 'bg-gray-200'}`} />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>

              <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6 sm:p-8">
                {formError && (
                  <p role="alert" className="mb-6 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                    {formError}
                  </p>
                )}

                {activeStep === 'identity' && (
                  <>
                    <StepHeader title="Identity" n={1} note="Your name, sign-in email and a password for your account." />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-5">
                      <TextField
                        fieldClassName="sm:col-span-2"
                        label="Full name"
                        required
                        value={form.full_name}
                        onValue={(v) => set('full_name', v)}
                        error={e('full_name')}
                        autoComplete="name"
                        maxLength={MAX_LENGTHS.shortText}
                        placeholder="Dr. Saima Hashmi"
                      />
                      <TextField
                        fieldClassName="sm:col-span-2"
                        label="Email"
                        required
                        type="email"
                        inputMode="email"
                        value={form.email}
                        onValue={(v) => set('email', v)}
                        error={e('email')}
                        autoComplete="email"
                        maxLength={MAX_LENGTHS.email}
                        placeholder="saima.hashmi@example.com"
                        hint="You'll sign in with this email once approved."
                      />
                      <div>
                        <TextField
                          label="Password"
                          required
                          type={showPassword ? 'text' : 'password'}
                          value={form.password}
                          onValue={(v) => set('password', v)}
                          error={e('password')}
                          autoComplete="new-password"
                          maxLength={MAX_LENGTHS.password}
                        />
                        <PasswordStrengthMeter password={form.password} />
                      </div>
                      <TextField
                        label="Confirm password"
                        required
                        type={showPassword ? 'text' : 'password'}
                        value={form.confirm}
                        onValue={(v) => set('confirm', v)}
                        error={e('confirm')}
                        autoComplete="new-password"
                        maxLength={MAX_LENGTHS.password}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="mb-6 inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-900"
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />} {showPassword ? 'Hide' : 'Show'} passwords
                    </button>
                    <div className="mb-8">
                      <AdultConfirm checked={form.adult} onChange={(v) => set('adult', v, 'is_adult_confirmed')} error={e('is_adult_confirmed')} />
                    </div>
                    <StepNav onContinue={() => proceed(checkIdentity, 'credentials')} continueLabel="Continue · Credentials" />
                  </>
                )}

                {activeStep === 'credentials' && (
                  <>
                    <StepHeader title="Credentials" n={2} note="Your licence and training. An admin checks these before approving you." />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-5">
                      <TextField
                        label="Licence number"
                        required
                        value={form.license_number}
                        onValue={setProfile('license_number')}
                        error={e('profile.license_number')}
                        maxLength={MAX_LENGTHS.shortText}
                        placeholder="PMDC-12345"
                      />
                      <SelectField
                        label="Issuing country"
                        required
                        value={form.license_issuing_country}
                        onValue={setProfile('license_issuing_country')}
                        options={countries}
                        error={e('profile.license_issuing_country')}
                      />
                      <TextField
                        fieldClassName="sm:col-span-2"
                        label="Issuing authority"
                        required
                        value={form.license_issuing_authority}
                        onValue={setProfile('license_issuing_authority')}
                        error={e('profile.license_issuing_authority')}
                        maxLength={MAX_LENGTHS.shortText}
                      />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
                      <TextField
                        label="Degree"
                        required
                        value={form.degree}
                        onValue={(v) => set('degree', v)}
                        error={e('degree')}
                        maxLength={MAX_LENGTHS.shortText}
                        placeholder="MS Clinical Psychology"
                      />
                      <TextField
                        label="University"
                        value={form.university}
                        onValue={(v) => set('university', v)}
                        maxLength={MAX_LENGTHS.shortText}
                        placeholder="University of the Punjab"
                      />
                      <TextField
                        label="Year"
                        inputMode="numeric"
                        value={form.graduation_year}
                        onValue={(v) => set('graduation_year', v.replace(/\D/g, '').slice(0, 4))}
                        placeholder="2014"
                      />
                    </div>
                    <div className="mb-8">
                      <ChipGroup
                        label={`I work with · pick ${MIN_SPECIALIZATIONS}–${MAX_SPECIALIZATIONS}`}
                        required
                        options={SPECIALIZATION_OPTIONS}
                        selected={form.specializations}
                        onToggle={(v) => toggle('specializations', v, MAX_SPECIALIZATIONS)}
                        error={e('profile.specializations')}
                      />
                    </div>
                    <div className="mb-8">
                      <label className="flex items-start gap-3 bg-[#EFE9DF] rounded-xl px-4 py-4 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.consent}
                          onChange={(ev) => set('consent', ev.target.checked)}
                          aria-invalid={!!e('consent')}
                          className="w-4 h-4 mt-0.5 rounded border-gray-300 accent-gray-900 shrink-0"
                        />
                        <span className="text-sm text-gray-700">
                          I consent to MindCare verifying my licence and qualifications, and understand an
                          admin may contact me for supporting documents before approving my account.
                        </span>
                      </label>
                      {e('consent') && (
                        <p role="alert" className="text-xs text-red-600 mt-1.5">
                          {e('consent')}
                        </p>
                      )}
                    </div>
                    <StepNav
                      onBack={() => goToStep('identity')}
                      backLabel="Back to Identity"
                      onContinue={() => proceed(checkCredentials, 'practice')}
                      continueLabel="Continue · Practice"
                    />
                  </>
                )}

                {activeStep === 'practice' && (
                  <>
                    <StepHeader title="Practice" n={3} note="How and where you practise, and a short bio patients will see." />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
                      <TextField
                        label="Years of experience"
                        required
                        inputMode="numeric"
                        value={form.years_of_experience}
                        onValue={(v) => setProfile('years_of_experience')(v.replace(/\D/g, '').slice(0, 2))}
                        error={e('profile.years_of_experience')}
                        placeholder="5"
                      />
                      <SelectField
                        label="Gender"
                        value={form.gender}
                        onValue={setProfile('gender')}
                        options={GENDER_OPTIONS}
                        error={e('profile.gender')}
                        hint="Optional."
                      />
                      <SelectField
                        label="Country"
                        required
                        value={form.country}
                        onValue={setProfile('country')}
                        options={countries}
                        error={e('profile.country')}
                      />
                      <TextField
                        label="City"
                        required
                        value={form.city}
                        onValue={setProfile('city')}
                        error={e('profile.city')}
                        autoComplete="address-level2"
                        maxLength={MAX_LENGTHS.shortText}
                        placeholder="Lahore"
                      />
                      <SelectField
                        fieldClassName="sm:col-span-2"
                        label="Time zone"
                        required
                        value={form.timezone}
                        onValue={setProfile('timezone')}
                        options={TIMEZONE_OPTIONS}
                        error={e('profile.timezone')}
                        hint="Used to show session times correctly."
                      />
                    </div>
                    <div className="mb-6">
                      <ChipGroup
                        label="Languages you practise in"
                        required
                        options={languageChips}
                        selected={form.languages}
                        onToggle={(v) => toggle('languages', v)}
                        error={e('profile.languages')}
                      />
                      {otherLanguages.length > 0 && (
                        <div className="mt-3 max-w-xs">
                          <SelectField
                            label="Add another language"
                            value=""
                            onValue={(v) => v && toggle('languages', v)}
                            options={otherLanguages}
                            placeholder="Choose…"
                          />
                        </div>
                      )}
                    </div>
                    <div className="mb-8">
                      <TextAreaField
                        label="Short bio"
                        rows={4}
                        value={form.bio}
                        onValue={setProfile('bio')}
                        error={e('profile.bio')}
                        hint="Optional. Patients see this on your profile."
                        maxLength={LIMITS.bio}
                        placeholder="e.g. CBT-focused therapist working with anxiety and burnout."
                      />
                    </div>
                    <StepNav
                      onBack={() => goToStep('credentials')}
                      backLabel="Back to Credentials"
                      onContinue={() => proceed(checkPractice, 'review')}
                      continueLabel="Continue · Review"
                    />
                  </>
                )}

                {activeStep === 'review' && (
                  <>
                    <StepHeader title="Review" n={4} note="Check your details, then submit your application for approval." />
                    <ReviewSection title="Identity" onEdit={() => goToStep('identity')} rows={[
                      ['Full name', form.full_name],
                      ['Email', form.email.trim().toLowerCase()],
                      ['18 or older', form.adult ? 'Confirmed' : '—'],
                    ]} />
                    <ReviewSection title="Credentials" onEdit={() => goToStep('credentials')} rows={[
                      ['Licence', `${form.license_number} · ${labelOf(countries, form.license_issuing_country)}`],
                      ['Issued by', form.license_issuing_authority],
                      ['Qualifications', qualificationsOf(form)],
                      ['Works with', form.specializations.map((s) => labelOf(SPECIALIZATION_OPTIONS, s)).join(', ')],
                    ]} />
                    <ReviewSection title="Practice" onEdit={() => goToStep('practice')} rows={[
                      ['Experience', form.years_of_experience ? `${form.years_of_experience} years` : '—'],
                      ['Languages', form.languages.map((l) => labelOf(allLanguages, l)).join(', ')],
                      ['Location', [form.city, labelOf(countries, form.country)].filter(Boolean).join(', ')],
                      ['Time zone', form.timezone],
                      ['Gender', form.gender ? labelOf(GENDER_OPTIONS, form.gender) : 'Not specified'],
                      ['Bio', form.bio],
                    ]} />
                    <StepNav
                      onBack={() => goToStep('practice')}
                      backLabel="Back to Practice"
                      onContinue={handleSubmit}
                      continueLabel="Submit application"
                      loading={submitting}
                    />
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {/* Right sidebar */}
        <aside className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-5">What happens next</h3>
            <ol className="space-y-5">
              {THERAPIST_WHAT_HAPPENS_NEXT.map((item, i) => (
                <li key={item.id} className="flex gap-4">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                      i === 0 ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-bold text-gray-900">{item.title}</p>
                    <p className="text-xs text-gray-500">{item.meta}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="bg-gray-900 rounded-2xl p-6">
            <p className="text-xs font-semibold tracking-widest text-orange-400 uppercase mb-4">Why therapists join</p>
            <p className="text-3xl font-black text-white mb-3">{THERAPIST_STATS[0].value} take-home</p>
            <p className="text-sm text-gray-400 leading-relaxed">
              One of the most generous splits anywhere. You set your own session price.
            </p>
          </div>
        </aside>
      </main>
    </div>
  );
};

// ——— Sub-components ———

const labelOf = (options: Option[], value: string) => options.find((o) => o.value === value)?.label ?? value;

const StepHeader: React.FC<{ title: string; n: number; note: string }> = ({ title, n, note }) => (
  <>
    <div className="flex items-center justify-between gap-3 mb-2">
      <h2 className="text-2xl font-black text-gray-900">{title}</h2>
      <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full shrink-0">Step {n} of 4</span>
    </div>
    <p className="text-sm text-gray-500 mb-8">{note}</p>
  </>
);

const StepNav: React.FC<{
  onBack?: () => void;
  backLabel?: string;
  onContinue: () => void;
  continueLabel: string;
  loading?: boolean;
}> = ({ onBack, backLabel = 'Back', onContinue, continueLabel, loading }) => (
  <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-4 border-t border-gray-100">
    {onBack ? (
      <button type="button" onClick={onBack} className="text-sm font-semibold text-gray-600 hover:text-gray-900 flex items-center justify-center gap-1.5">
        <ArrowLeft size={14} /> {backLabel}
      </button>
    ) : (
      <span />
    )}
    <Button variant="primary" size="md" onClick={onContinue} loading={loading}>
      {continueLabel} <ArrowRight size={14} />
    </Button>
  </div>
);

const ReviewSection: React.FC<{ title: string; rows: [string, string][]; onEdit: () => void }> = ({ title, rows, onEdit }) => (
  <section className="mb-6 rounded-2xl border border-gray-100 bg-[#FBF8F3] p-5">
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-bold text-gray-900">{title}</h3>
      <button type="button" onClick={onEdit} className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500 hover:text-gray-900">
        <Pencil size={12} /> Edit
      </button>
    </div>
    <dl className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
      {rows.map(([k, v]) => (
        <React.Fragment key={k}>
          <dt className="text-gray-500">{k}</dt>
          <dd className="text-gray-900 break-words">{v || '—'}</dd>
        </React.Fragment>
      ))}
    </dl>
  </section>
);

export default TherapistRegisterPage;
