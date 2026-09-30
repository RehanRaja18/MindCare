// ============================================================
// MindCare — NGO sign-up (For NGOs page)
// Submits POST /accounts/register/ with role "ngo" and the nested
// profile the backend expects. NGO accounts start "pending" until an
// admin approves them.
// ============================================================

import React, { useState } from 'react';
import { CheckCircle2, Plus, Trash2 } from 'lucide-react';
import Button from '../common/Button';
import PasswordStrengthMeter from '../common/PasswordStrengthMeter';
import { AdultConfirm, SelectField, TextAreaField, TextField } from '../forms/Fields';
import { register, flattenFieldErrors } from '../../services/api.service';
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirmation,
  validateRequiredText,
  sanitizeText,
  MAX_LENGTHS,
} from '../../utils/validation';
import { COUNTRY_OPTIONS, DEFAULT_TIMEZONE, TIMEZONE_OPTIONS } from '../../utils/locale';
import type { NgoProfile, RegisterPayload } from '../../types';

interface Area {
  country: string;
  city: string;
}

const initial = {
  full_name: '',
  email: '',
  password: '',
  confirm: '',
  adult: false,
  organization_name: '',
  registration_number: '',
  registration_country: 'PK',
  registering_authority: '',
  country: 'PK',
  city: '',
  timezone: DEFAULT_TIMEZONE,
  official_phone: '',
  official_email: '',
  website: '',
  description: '',
  service_areas: [{ country: 'PK', city: '' }] as Area[],
};

type FormState = typeof initial;
type Errors = Record<string, string | undefined>;

const PHONE_RE = /^\+?[0-9 ()-]{7,20}$/;

const NgoRegisterForm: React.FC = () => {
  const [form, setForm] = useState<FormState>(initial);
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [honeypot, setHoneypot] = useState(''); // hidden field — real users never fill this in
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const clear = (key: string) => errors[key] && setErrors((prev) => ({ ...prev, [key]: undefined }));
  const set = <K extends keyof FormState>(key: K, errorKey: string = `profile.${key}`) => (value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    clear(errorKey);
  };
  const setArea = (i: number, patch: Partial<Area>) => {
    setForm((prev) => ({
      ...prev,
      service_areas: prev.service_areas.map((a, j) => (j === i ? { ...a, ...patch } : a)),
    }));
    Object.keys(patch).forEach((k) => clear(`profile.service_areas.${i}.${k}`));
    clear('profile.service_areas');
  };

  const validate = (): Errors => {
    const next: Errors = {
      full_name: validateRequiredText(form.full_name, 'Contact name') ?? undefined,
      email: validateEmail(form.email) ?? undefined,
      password: validatePassword(form.password) ?? undefined,
      confirm: validatePasswordConfirmation(form.password, form.confirm) ?? undefined,
      is_adult_confirmed: form.adult ? undefined : 'You must be 18 or older to register.',
      'profile.organization_name': validateRequiredText(form.organization_name, 'Organisation name') ?? undefined,
      'profile.registration_number': validateRequiredText(form.registration_number, 'Registration number') ?? undefined,
      'profile.registering_authority': validateRequiredText(form.registering_authority, 'Registering authority') ?? undefined,
      'profile.city': validateRequiredText(form.city, 'City') ?? undefined,
      'profile.official_phone': PHONE_RE.test(form.official_phone.trim())
        ? undefined
        : 'Enter a phone number, e.g. +92 21 1123 4567.',
      'profile.official_email': validateEmail(form.official_email) ?? undefined,
      'profile.website':
        form.website.trim() && !/^https?:\/\/[^\s.]+\.[^\s]+$/i.test(form.website.trim())
          ? 'Enter a full web address starting with https://'
          : undefined,
      'profile.description': validateRequiredText(form.description, 'Description', MAX_LENGTHS.longText) ?? undefined,
    };
    form.service_areas.forEach((a, i) => {
      if (!a.country) next[`profile.service_areas.${i}.country`] = 'Choose a country.';
    });
    return next;
  };

  const buildPayload = (): RegisterPayload => {
    const profile: NgoProfile = {
      organization_name: sanitizeText(form.organization_name),
      registration_number: form.registration_number.trim(),
      registration_country: form.registration_country,
      registering_authority: sanitizeText(form.registering_authority),
      country: form.country,
      city: sanitizeText(form.city),
      timezone: form.timezone,
      official_phone: form.official_phone.replace(/[ ()-]/g, ''),
      official_email: form.official_email.trim().toLowerCase(),
      website: form.website.trim(),
      description: sanitizeText(form.description),
      // City is optional per area — omit it rather than sending ""
      service_areas: form.service_areas.map((a) => (a.city.trim() ? { country: a.country, city: sanitizeText(a.city) } : { country: a.country })),
    };
    // Website is optional in the form; leave the key out when empty.
    if (!profile.website) delete (profile as Partial<NgoProfile>).website;
    return {
      email: form.email.trim().toLowerCase(),
      password: form.password,
      full_name: sanitizeText(form.full_name),
      role: 'ngo',
      is_adult_confirmed: true,
      profile,
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Bots fill every field, including hidden ones — pretend success.
    if (honeypot) {
      setSubmitted(true);
      return;
    }

    const found = validate();
    if (Object.values(found).some(Boolean)) {
      setErrors(found);
      setFormError('Please fix the highlighted fields.');
      return;
    }

    setSubmitting(true);
    setFormError(null);
    const res = await register(buildPayload());
    setSubmitting(false);

    if (res.data) {
      setSubmitted(true);
      return;
    }
    if (res.status === 400 && res.errorBody) {
      const fieldErrors = flattenFieldErrors(res.errorBody);
      setErrors(fieldErrors);
      setFormError(fieldErrors._ ?? 'Please fix the highlighted fields.');
      return;
    }
    setFormError(res.error ?? 'Something went wrong. Please try again.');
  };

  if (submitted) {
    return (
      <div className="py-6 text-center">
        <CheckCircle2 size={44} className="mx-auto text-emerald-500 mb-4" aria-hidden="true" />
        <p className="text-gray-900 font-semibold mb-2">Registration received.</p>
        <p className="text-sm text-gray-500 max-w-sm mx-auto">
          Your NGO account is <strong>pending admin approval</strong>. We&apos;ll be in touch at{' '}
          {form.email.trim().toLowerCase() || 'your email'} once it has been reviewed.
        </p>
      </div>
    );
  }

  const e = (key: string) => errors[key];

  return (
    <form onSubmit={handleSubmit} className="space-y-8" noValidate>
      {/* Honeypot — invisible to real users; tabIndex/aria keep it out of keyboard + screen-reader flow. */}
      <input
        type="text"
        name="hp_contact_reference"
        value={honeypot}
        onChange={(ev) => setHoneypot(ev.target.value)}
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="absolute -left-[9999px] w-px h-px opacity-0"
      />

      {formError && (
        <p role="alert" className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          {formError}
        </p>
      )}

      <Section title="Contact person" note="The person who will sign in for your organisation.">
        <TextField fieldClassName="sm:col-span-2" label="Full name" required value={form.full_name} onValue={set('full_name', 'full_name')} error={e('full_name')} autoComplete="name" maxLength={MAX_LENGTHS.shortText} />
        <TextField fieldClassName="sm:col-span-2" label="Sign-in email" required type="email" inputMode="email" value={form.email} onValue={set('email', 'email')} error={e('email')} autoComplete="email" maxLength={MAX_LENGTHS.email} />
        <div>
          <TextField label="Password" required type="password" value={form.password} onValue={set('password', 'password')} error={e('password')} autoComplete="new-password" maxLength={MAX_LENGTHS.password} />
          <PasswordStrengthMeter password={form.password} />
        </div>
        <TextField label="Confirm password" required type="password" value={form.confirm} onValue={set('confirm', 'confirm')} error={e('confirm')} autoComplete="new-password" maxLength={MAX_LENGTHS.password} />
      </Section>

      <Section title="Organisation">
        <TextField fieldClassName="sm:col-span-2" label="Organisation name" required value={form.organization_name} onValue={set('organization_name')} error={e('profile.organization_name')} autoComplete="organization" maxLength={MAX_LENGTHS.shortText} />
        <TextField label="Registration number" required value={form.registration_number} onValue={set('registration_number')} error={e('profile.registration_number')} maxLength={MAX_LENGTHS.shortText} placeholder="SECP-0001" />
        <SelectField label="Registered in" required value={form.registration_country} onValue={set('registration_country')} options={COUNTRY_OPTIONS} error={e('profile.registration_country')} />
        <TextField fieldClassName="sm:col-span-2" label="Registering authority" required value={form.registering_authority} onValue={set('registering_authority')} error={e('profile.registering_authority')} maxLength={MAX_LENGTHS.shortText} placeholder="SECP" />
        <SelectField label="Country" required value={form.country} onValue={set('country')} options={COUNTRY_OPTIONS} error={e('profile.country')} />
        <TextField label="City" required value={form.city} onValue={set('city')} error={e('profile.city')} autoComplete="address-level2" maxLength={MAX_LENGTHS.shortText} placeholder="Karachi" />
        <SelectField fieldClassName="sm:col-span-2" label="Time zone" required value={form.timezone} onValue={set('timezone')} options={TIMEZONE_OPTIONS} error={e('profile.timezone')} />
        <TextField label="Official phone" required type="tel" inputMode="tel" value={form.official_phone} onValue={set('official_phone')} error={e('profile.official_phone')} autoComplete="tel" placeholder="+92 21 1123 4567" />
        <TextField label="Official email" required type="email" inputMode="email" value={form.official_email} onValue={set('official_email')} error={e('profile.official_email')} maxLength={MAX_LENGTHS.email} placeholder="info@yourngo.org" />
        <TextField fieldClassName="sm:col-span-2" label="Website" type="url" inputMode="url" value={form.website} onValue={set('website')} error={e('profile.website')} autoComplete="url" placeholder="https://yourngo.org" hint="Optional." />
        <TextAreaField fieldClassName="sm:col-span-2" label="What you do" required rows={4} value={form.description} onValue={set('description')} error={e('profile.description')} maxLength={MAX_LENGTHS.longText} placeholder="In one paragraph: who you serve, and what you offer." />
      </Section>

      <div>
        <h3 className="text-xs font-bold tracking-widest text-gray-900 uppercase mb-1">Where you work</h3>
        <p className="text-xs text-gray-500 mb-4">Add each country you serve. Leave the city blank if you cover the whole country.</p>
        {e('profile.service_areas') && (
          <p role="alert" className="text-xs text-red-600 mb-3">
            {e('profile.service_areas')}
          </p>
        )}
        <div className="space-y-3">
          {form.service_areas.map((a, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-3 items-start">
              <SelectField label={`Area ${i + 1} · country`} value={a.country} onValue={(v) => setArea(i, { country: v })} options={COUNTRY_OPTIONS} error={e(`profile.service_areas.${i}.country`)} />
              <TextField label="City" value={a.city} onValue={(v) => setArea(i, { city: v })} error={e(`profile.service_areas.${i}.city`)} maxLength={MAX_LENGTHS.shortText} placeholder="Whole country" />
              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, service_areas: prev.service_areas.filter((_, j) => j !== i) }))}
                disabled={form.service_areas.length === 1}
                aria-label={`Remove area ${i + 1}`}
                className="mt-7 p-3 rounded-xl text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-gray-400"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setForm((prev) => ({ ...prev, service_areas: [...prev.service_areas, { country: 'PK', city: '' }] }))}
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-gray-700 hover:text-gray-900"
        >
          <Plus size={15} /> Add another area
        </button>
      </div>

      <AdultConfirm checked={form.adult} onChange={set('adult', 'is_adult_confirmed')} error={e('is_adult_confirmed')} />

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
        <p className="text-xs text-gray-500">An admin reviews every NGO before the account is activated.</p>
        <Button type="submit" variant="primary" size="md" className="shrink-0" loading={submitting}>
          Register →
        </Button>
      </div>
    </form>
  );
};

const Section: React.FC<{ title: string; note?: string; children: React.ReactNode }> = ({ title, note, children }) => (
  <div>
    <h3 className="text-xs font-bold tracking-widest text-gray-900 uppercase mb-1">{title}</h3>
    {note && <p className="text-xs text-gray-500 mb-4">{note}</p>}
    <div className={`grid grid-cols-1 sm:grid-cols-2 gap-4 ${note ? '' : 'mt-4'}`}>{children}</div>
  </div>
);

export default NgoRegisterForm;
