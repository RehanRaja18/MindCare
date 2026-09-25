// ============================================================
// MindCare — Therapist Registration Wizard ("Let's get you verified.")
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Upload, X, ArrowRight, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import Button from '../components/common/Button';
import PasswordStrengthMeter from '../components/common/PasswordStrengthMeter';
import {
  ROUTES,
  THERAPIST_ONBOARDING_STEPS,
  THERAPIST_WHAT_HAPPENS_NEXT,
  THERAPIST_SPECIALTIES,
  THERAPIST_FOCUS_AREAS,
  THERAPIST_STATS,
} from '../constants';
import {
  validatePmdcLicense,
  validateRequiredText,
  validateEmail,
  validatePassword,
  validatePasswordConfirmation,
  sanitizeText,
  MAX_LENGTHS,
} from '../utils/validation';
import type { TherapistCredentials, TherapistRegisterStep } from '../types';

const MIN_FOCUS_AREAS = 3;
const MAX_FOCUS_AREAS = 6;

const initialCredentials: TherapistCredentials = {
  pmdcLicenseNumber: '102-CP-44871',
  pmdcVerified: true,
  specialty: THERAPIST_SPECIALTIES[0],
  degree: '',
  university: '',
  graduationYear: '',
  focusAreas: ['Anxiety', 'Burnout', 'Trauma', 'EMDR'],
  consentBackgroundCheck: true,
};

interface IdentityForm {
  fullName: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
}

const initialIdentity: IdentityForm = {
  fullName: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
};

const TherapistRegisterPage: React.FC = () => {
  const [activeStep, setActiveStep] = useState<TherapistRegisterStep>('identity');
  const [form, setForm] = useState<TherapistCredentials>(initialCredentials);
  const [fieldErrors, setFieldErrors] = useState<{ pmdcLicenseNumber?: string; degree?: string }>({});

  const [identity, setIdentity] = useState<IdentityForm>(initialIdentity);
  const [identityErrors, setIdentityErrors] = useState<Partial<Record<keyof IdentityForm, string>>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [documents, setDocuments] = useState({
    pmdcLicense: { name: 'pmdc-44871.pdf', size: '482 KB' } as { name: string; size: string } | null,
    degreeCertificate: { name: 'msc-clinical-fjwu.pdf', size: '1.2 MB' } as { name: string; size: string } | null,
    cnic: null as { name: string; size: string } | null,
    liabilityInsurance: null as { name: string; size: string } | null,
  });

  const stepIndex = THERAPIST_ONBOARDING_STEPS.findIndex((s) => s.id === activeStep);

  // ——— Identity step ———
  const handleIdentityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setIdentity((prev) => ({ ...prev, [name]: value }));
    if (name in identityErrors) {
      setIdentityErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const validateIdentityStep = (): boolean => {
    const errors: typeof identityErrors = {};
    const nameError = validateRequiredText(identity.fullName, 'Full name');
    if (nameError) errors.fullName = nameError;

    const emailError = validateEmail(identity.email);
    if (emailError) errors.email = emailError;

    const passwordError = validatePassword(identity.password);
    if (passwordError) errors.password = passwordError;

    const confirmError = validatePasswordConfirmation(identity.password, identity.confirmPassword);
    if (confirmError) errors.confirmPassword = confirmError;

    setIdentityErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleContinueToCredentials = () => {
    if (!validateIdentityStep()) return;
    setIdentity((prev) => ({ ...prev, fullName: sanitizeText(prev.fullName) }));
    goToStep('credentials');
  };

  // ——— Credentials step ———
  const validateCredentialsStep = (): boolean => {
    const errors: typeof fieldErrors = {};
    const licenseError = validatePmdcLicense(form.pmdcLicenseNumber);
    if (licenseError) errors.pmdcLicenseNumber = licenseError;
    const degreeError = validateRequiredText(form.degree, 'Degree');
    if (degreeError) errors.degree = degreeError;
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleContinueToPractice = () => {
    if (!validateCredentialsStep()) return;
    setForm((prev) => ({ ...prev, degree: sanitizeText(prev.degree), university: sanitizeText(prev.university) }));
    goToStep('practice');
  };

  const toggleFocusArea = (area: string) => {
    setForm((prev) => {
      const already = prev.focusAreas.includes(area);
      if (already) {
        return { ...prev, focusAreas: prev.focusAreas.filter((a) => a !== area) };
      }
      if (prev.focusAreas.length >= MAX_FOCUS_AREAS) return prev;
      return { ...prev, focusAreas: [...prev.focusAreas, area] };
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (name in fieldErrors) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const removeDocument = (key: keyof typeof documents) => {
    setDocuments((prev) => ({ ...prev, [key]: null }));
  };

  const attachDocument = (key: keyof typeof documents) => {
    setDocuments((prev) => ({ ...prev, [key]: { name: 'uploaded-file.pdf', size: '—' } }));
  };

  const goToStep = (step: TherapistRegisterStep) => setActiveStep(step);

  const canContinue = form.focusAreas.length >= MIN_FOCUS_AREAS && documents.pmdcLicense && documents.degreeCertificate;

  return (
    <div className="min-h-screen bg-[#F5F0E8]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-10 py-6">
        <Link to={ROUTES.HOME} className="text-xl font-bold tracking-tight text-gray-900">
          MindCare<span className="text-orange-500">.</span>
        </Link>
        <p className="text-sm text-gray-500">
          Already a therapist here?{' '}
          <Link to={ROUTES.THERAPIST_LOGIN} className="font-semibold text-gray-900 underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Left / center column */}
        <div className="lg:col-span-2">
          <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
            Therapist · Apply to practice
          </p>
          <h1 className="text-4xl sm:text-5xl font-black text-gray-900 mb-4">
            Let&apos;s get you <span className="italic font-serif font-normal">verified.</span>
          </h1>
          <p className="text-gray-600 max-w-xl mb-8">
            MindCare only accepts PMDC-licensed clinicians. Verification takes 2–3 working days —
            we&apos;ll auto-check what we can and a human reviews the rest.
          </p>

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
                    <span className={`flex-1 h-0.5 ${isDone ? 'bg-emerald-600' : 'bg-gray-200'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Card */}
          <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8">
            {activeStep === 'identity' && (
              <>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-2xl font-black text-gray-900">Identity</h2>
                  <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                    Step 1 of 4
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-8">
                  Confirm your name and contact details, then set a password for your account.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-5">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Full name *
                    </label>
                    <input
                      name="fullName"
                      value={identity.fullName}
                      onChange={handleIdentityChange}
                      autoComplete="name"
                      maxLength={MAX_LENGTHS.shortText}
                      placeholder="Dr. Saima Hashmi"
                      aria-invalid={!!identityErrors.fullName}
                      className={`w-full px-4 py-3 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                        identityErrors.fullName ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
                      }`}
                    />
                    {identityErrors.fullName && (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {identityErrors.fullName}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Email *
                    </label>
                    <input
                      name="email"
                      type="email"
                      value={identity.email}
                      onChange={handleIdentityChange}
                      autoComplete="email"
                      maxLength={MAX_LENGTHS.email}
                      placeholder="saima.hashmi@gmail.com"
                      aria-invalid={!!identityErrors.email}
                      className={`w-full px-4 py-3 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                        identityErrors.email ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
                      }`}
                    />
                    {identityErrors.email && (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {identityErrors.email}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Phone <span className="font-normal normal-case text-gray-400">(optional)</span>
                    </label>
                    <input
                      name="phone"
                      type="tel"
                      value={identity.phone}
                      onChange={handleIdentityChange}
                      autoComplete="tel"
                      maxLength={20}
                      placeholder="+92 3XX XXXXXXX"
                      className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 bg-gray-50"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Password *
                    </label>
                    <div className="relative">
                      <input
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        value={identity.password}
                        onChange={handleIdentityChange}
                        autoComplete="new-password"
                        maxLength={MAX_LENGTHS.password}
                        placeholder="At least 12 characters"
                        aria-invalid={!!identityErrors.password}
                        className={`w-full px-4 py-3 pr-11 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                          identityErrors.password ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
                        }`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    <PasswordStrengthMeter password={identity.password} />
                    {identityErrors.password && (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {identityErrors.password}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Confirm password *
                    </label>
                    <div className="relative">
                      <input
                        name="confirmPassword"
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={identity.confirmPassword}
                        onChange={handleIdentityChange}
                        autoComplete="new-password"
                        maxLength={MAX_LENGTHS.password}
                        placeholder="Re-enter your password"
                        aria-invalid={!!identityErrors.confirmPassword}
                        className={`w-full px-4 py-3 pr-11 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                          identityErrors.confirmPassword ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
                        }`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((v) => !v)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      >
                        {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {identityErrors.confirmPassword && (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {identityErrors.confirmPassword}
                      </p>
                    )}
                  </div>
                </div>

                <p className="text-xs text-gray-400 mb-8">
                  Use at least 12 characters with a mix of upper/lowercase letters and a number. A real
                  backend must also reject passwords found in known data breaches.
                </p>

                <div className="flex items-center justify-end pt-4 border-t border-gray-100">
                  <Button variant="primary" size="md" onClick={handleContinueToCredentials}>
                    Continue · Credentials <ArrowRight size={14} />
                  </Button>
                </div>
              </>
            )}

            {activeStep === 'credentials' && (
              <>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-2xl font-black text-gray-900">Credentials</h2>
                  <span className="text-xs font-semibold text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                    Step 2 of 4
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-8">
                  We auto-verify PMDC and HEC. The rest you upload — we&apos;ll handle the eye-checking.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      PMDC license number *
                    </label>
                    <div className="relative">
                      <input
                        name="pmdcLicenseNumber"
                        value={form.pmdcLicenseNumber}
                        onChange={handleChange}
                        aria-invalid={!!fieldErrors.pmdcLicenseNumber}
                        className={`w-full pl-4 pr-24 py-3 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                          fieldErrors.pmdcLicenseNumber
                            ? 'border-red-300 focus:ring-red-500'
                            : 'border-gray-200 focus:ring-gray-900'
                        }`}
                      />
                      {form.pmdcVerified && !fieldErrors.pmdcLicenseNumber && (
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs font-semibold text-emerald-700">
                          <Check size={14} /> Verified
                        </span>
                      )}
                    </div>
                    {fieldErrors.pmdcLicenseNumber ? (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {fieldErrors.pmdcLicenseNumber}
                      </p>
                    ) : (
                      <p className="text-xs text-emerald-700 mt-1.5">Valid through Aug 2027 · pulled from PMDC.gov.pk</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Specialty *
                    </label>
                    <select
                      name="specialty"
                      value={form.specialty}
                      onChange={handleChange}
                      className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 bg-gray-50"
                    >
                      {THERAPIST_SPECIALTIES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Degree *</label>
                    <input
                      name="degree"
                      value={form.degree}
                      onChange={handleChange}
                      placeholder="MS Clinical Psychology"
                      aria-invalid={!!fieldErrors.degree}
                      className={`w-full px-4 py-3 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-gray-50 ${
                        fieldErrors.degree ? 'border-red-300 focus:ring-red-500' : 'border-gray-200 focus:ring-gray-900'
                      }`}
                    />
                    {fieldErrors.degree && (
                      <p role="alert" className="text-xs text-red-600 mt-1.5">
                        {fieldErrors.degree}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">University</label>
                    <input
                      name="university"
                      value={form.university}
                      onChange={handleChange}
                      placeholder="FJWU, Rawalpindi"
                      className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 bg-gray-50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">Year</label>
                    <input
                      name="graduationYear"
                      value={form.graduationYear}
                      onChange={handleChange}
                      placeholder="2014"
                      className="w-full px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 bg-gray-50"
                    />
                  </div>
                </div>

                <div className="mb-8">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">
                    I work with · pick {MIN_FOCUS_AREAS}–{MAX_FOCUS_AREAS} *
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {THERAPIST_FOCUS_AREAS.map((area) => {
                      const selected = form.focusAreas.includes(area);
                      return (
                        <button
                          type="button"
                          key={area}
                          onClick={() => toggleFocusArea(area)}
                          className={`px-4 py-2 rounded-full text-sm font-semibold border transition-colors ${
                            selected
                              ? 'bg-gray-900 text-white border-gray-900'
                              : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'
                          }`}
                        >
                          {area} {selected && '✓'}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mb-6">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">
                    Supporting documents *
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <DocSlot
                      label="PMDC license · scan"
                      file={documents.pmdcLicense}
                      onRemove={() => removeDocument('pmdcLicense')}
                      onAttach={() => attachDocument('pmdcLicense')}
                    />
                    <DocSlot
                      label="Degree certificate"
                      file={documents.degreeCertificate}
                      onRemove={() => removeDocument('degreeCertificate')}
                      onAttach={() => attachDocument('degreeCertificate')}
                    />
                    <DocSlot
                      label="CNIC (both sides)"
                      file={documents.cnic}
                      onRemove={() => removeDocument('cnic')}
                      onAttach={() => attachDocument('cnic')}
                    />
                    <DocSlot
                      label="Liability insurance · optional"
                      hint="PDF, max 5 MB · optional"
                      file={documents.liabilityInsurance}
                      onRemove={() => removeDocument('liabilityInsurance')}
                      onAttach={() => attachDocument('liabilityInsurance')}
                    />
                  </div>
                </div>

                <label className="flex items-start gap-3 bg-[#EFE9DF] rounded-xl px-4 py-4 mb-8 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.consentBackgroundCheck}
                    onChange={(e) => setForm((prev) => ({ ...prev, consentBackgroundCheck: e.target.checked }))}
                    className="w-4 h-4 mt-0.5 rounded border-gray-300 accent-gray-900"
                  />
                  <span className="text-sm text-gray-700">
                    I consent to a <span className="font-bold">background check</span> by Verisys on
                    behalf of MindCare. I understand that flagged results will pause my application
                    until reviewed by a senior admin.
                  </span>
                </label>

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => goToStep('identity')}
                    className="text-sm font-semibold text-gray-600 hover:text-gray-900 flex items-center gap-1.5"
                  >
                    <ArrowLeft size={14} /> Back to Identity
                  </button>
                  <div className="flex gap-3 w-full sm:w-auto">
                    <Button variant="secondary" size="md" className="flex-1 sm:flex-none">
                      Save &amp; continue later
                    </Button>
                    <Button
                      variant="primary"
                      size="md"
                      className="flex-1 sm:flex-none"
                      disabled={!canContinue}
                      onClick={handleContinueToPractice}
                    >
                      Continue · Practice <ArrowRight size={14} />
                    </Button>
                  </div>
                </div>
              </>
            )}

            {activeStep === 'practice' && (
              <PlaceholderStep
                title="Practice"
                description="Set your session pricing, weekly availability, and languages you practice in."
                onBack={() => goToStep('credentials')}
                onContinue={() => goToStep('review')}
              />
            )}

            {activeStep === 'review' && (
              <PlaceholderStep
                title="Review"
                description="Double-check everything below, then submit your application for verification."
                onBack={() => goToStep('practice')}
                continueLabel="Submit application"
              />
            )}
          </div>
        </div>

        {/* Right sidebar */}
        <aside className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-5">
              What happens next
            </h3>
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
            <p className="text-xs font-semibold tracking-widest text-orange-400 uppercase mb-4">
              Why therapists join
            </p>
            <p className="text-3xl font-black text-white mb-3">{THERAPIST_STATS[0].value} take-home</p>
            <p className="text-sm text-gray-400 leading-relaxed mb-4">
              One of the most generous splits anywhere. You set your own price between sessions Rs
              3,000–8,000.
            </p>
            <p className="text-sm text-gray-300">
              Avg therapist take-home · <span className="font-bold text-white">{THERAPIST_STATS[1].value}/month</span>
            </p>
          </div>

          <p className="text-sm text-gray-500 px-1">
            Need help? Email{' '}
            <a href="mailto:therapists@mindcare.pk" className="underline underline-offset-2 text-gray-700">
              therapists@mindcare.pk
            </a>{' '}
            or call <span className="font-semibold text-gray-700">0800-MINDCARE</span>.
          </p>
        </aside>
      </main>
    </div>
  );
};

// ——— Sub-components ———

interface DocSlotProps {
  label: string;
  hint?: string;
  file: { name: string; size: string } | null;
  onRemove: () => void;
  onAttach: () => void;
}

const DocSlot: React.FC<DocSlotProps> = ({ label, hint, file, onRemove, onAttach }) => {
  if (file) {
    return (
      <div className="flex items-center justify-between gap-3 border border-emerald-200 bg-emerald-50/60 rounded-xl px-4 py-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <span className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0">
            <Check size={13} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 truncate">{label}</p>
            <p className="text-xs text-gray-500 truncate">
              {file.name} · {file.size}
            </p>
          </div>
        </div>
        <button type="button" onClick={onRemove} className="text-gray-400 hover:text-gray-700 shrink-0" aria-label={`Remove ${label}`}>
          <X size={16} />
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onAttach}
      className="flex items-center gap-3 border border-dashed border-gray-300 rounded-xl px-4 py-3.5 text-left hover:border-gray-400 transition-colors"
    >
      <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center shrink-0">
        <Upload size={13} />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900">{label}</p>
        <p className="text-xs text-gray-500">{hint ?? 'Drag or click to upload'}</p>
      </div>
    </button>
  );
};

interface PlaceholderStepProps {
  title: string;
  description: string;
  onBack?: () => void;
  onContinue?: () => void;
  continueLabel?: string;
}

const PlaceholderStep: React.FC<PlaceholderStepProps> = ({
  title,
  description,
  onBack,
  onContinue,
  continueLabel = 'Continue',
}) => (
  <div>
    <h2 className="text-2xl font-black text-gray-900 mb-2">{title}</h2>
    <p className="text-sm text-gray-500 mb-10">{description}</p>
    <div className="flex items-center justify-between pt-4 border-t border-gray-100">
      {onBack ? (
        <button type="button" onClick={onBack} className="text-sm font-semibold text-gray-600 hover:text-gray-900 flex items-center gap-1.5">
          <ArrowLeft size={14} /> Back
        </button>
      ) : (
        <span />
      )}
      {onContinue && (
        <Button variant="primary" size="md" onClick={onContinue}>
          {continueLabel} <ArrowRight size={14} />
        </Button>
      )}
    </div>
  </div>
);

export default TherapistRegisterPage;