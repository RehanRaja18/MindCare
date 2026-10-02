// ============================================================
// MindCare — Get Started Page
// Two doors, side by side:
//   left  — patients: scan the QR code / download the mobile app
//   right — psychologists: the full registration wizard
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import Logo from '../components/common/Logo';
import QRCode from '../components/mockup/QRCode';
import Button from '../components/common/Button';
import Reveal from '../components/motion/Reveal';
import TherapistRegisterWizard from '../components/therapist/TherapistRegisterWizard';
import { ROUTES } from '../constants';
import { requestAppLink } from '../services/api.service';

// ——— Email capture form (dummy flow for data testing) ———
const EmailLinkForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setLoading(true);
    setError(null);


    const result = await requestAppLink(email);

    setLoading(false);
    if (result.error) {
      setError('Something went wrong. Try again.');
    } else {
      setSent(true);
    }
  };

  if (sent) {
    return (
      <p className="text-sm text-emerald-700 font-semibold mt-1">
        ✓ Link sent! Check your inbox for {email}.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 mt-2"
      aria-label="Email me the download link"
    >
      <label htmlFor="app-email" className="sr-only">
        Email address
      </label>
      <input
        id="app-email"
        type="email"
        required
        autoComplete="email"
        placeholder="your@email.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 bg-white"
      />
      <Button type="submit" size="sm" variant="primary" loading={loading}>
        <Mail size={14} />
        Send
      </Button>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </form>
  );
};

// ——— Store button ———
interface StoreButtonProps {
  platform: 'google' | 'apple';
}

const StoreButton: React.FC<StoreButtonProps> = ({ platform }) => (
  <button
    className="flex items-center gap-3 bg-gray-900 text-white px-5 py-3.5 rounded-2xl hover:bg-gray-800 transition-colors min-w-[160px]"
    aria-label={platform === 'google' ? 'Get it on Google Play' : 'Download on the App Store'}
    onClick={() => alert(`[Demo] Would redirect to ${platform === 'google' ? 'Google Play' : 'App Store'}`)}
  >
    <span className="text-lg" aria-hidden="true">
      {platform === 'google' ? '▶' : ''}
      {platform === 'apple' ? '' : ''}
    </span>
    <div className="text-left">
      <p className="text-[9px] font-semibold uppercase tracking-widest text-gray-400">
        {platform === 'google' ? 'Get it on' : 'Download on the'}
      </p>
      <p className="text-base font-bold leading-tight">
        {platform === 'google' ? 'Google Play' : 'App Store'}
      </p>
    </div>
  </button>
);

// ——— Main Page ———
const ClientAppPage: React.FC = () => (
  <div className="min-h-screen mc-page-glow flex flex-col">
    {/* Header */}
    <header className="flex items-center justify-between px-4 sm:px-10 py-5 border-b border-gray-200/60">
      <Logo />
      <Link to={ROUTES.HOME} className="text-sm text-gray-500 hover:text-gray-900 transition-colors">
        ← Back to home
      </Link>
    </header>

    {/* Split layout */}
    <main className="flex-1 grid lg:grid-cols-2">
      {/* Left — patients: get the app */}
      <Reveal className="px-4 sm:px-14 py-12 lg:py-16 lg:sticky lg:top-0 lg:self-start" y={16}>
        <div className="max-w-xl mx-auto lg:mx-0">
          {/* On small screens the registration sits below — offer a shortcut */}
          <button
            type="button"
            onClick={() => document.getElementById('apply-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
            className="lg:hidden mb-8 inline-flex items-center gap-2 rounded-full bg-white/80 border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-800 hover:border-gray-400 transition-colors"
          >
            Are you a psychologist? Apply below ↓
          </button>

          <p className="text-[10px] font-black tracking-[0.25em] text-gray-500 uppercase mb-6">
            Looking for support · Get the app
          </p>

          <h1 className="text-4xl sm:text-5xl font-black text-gray-900 leading-tight mb-6">
            MindCare lives in{' '}
            <em style={{ fontFamily: "'Playfair Display', serif" }}>your pocket.</em>
          </h1>

          <p className="text-gray-600 text-base leading-relaxed mb-8 max-w-md">
            Care happens in the mobile app — sessions, daily check-ins, journaling and quiet
            circles. Scan the code, finish your intake, and book your first session.
          </p>

          {/* QR card */}
          <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6 flex flex-col sm:flex-row items-center gap-6 max-w-md mb-8">
            <QRCode className="w-40 h-40 shrink-0" />
            <div className="text-center sm:text-left">
              <p className="font-bold text-gray-900 text-lg">Scan to download</p>
              <p className="text-sm text-gray-500 mt-1">
                Point your phone&apos;s camera at the code. It detects your device and takes you to the
                right store.
              </p>
            </div>
          </div>

          {/* Store buttons */}
          <div className="flex flex-wrap gap-3 mb-6">
            <StoreButton platform="google" />
            <StoreButton platform="apple" />
          </div>

          {/* Email link */}
          <div>
            <p className="text-xs text-gray-500 mb-1">iOS 15+ · Android 9+ &nbsp;·&nbsp; Free · 7-day trial</p>
            <button
              className="text-xs text-gray-500 underline underline-offset-2 hover:text-gray-900 transition-colors"
              onClick={(e) => {
                const form = (e.currentTarget.closest('div') as HTMLElement).querySelector('form');
                form?.classList.toggle('hidden');
              }}
            >
              Email me the link instead
            </button>
            <div className="hidden">
              <EmailLinkForm />
            </div>
          </div>
        </div>
      </Reveal>

      {/* Right — psychologists: register */}
      <section className="bg-[#EDEAE0] px-4 sm:px-10 py-12 lg:py-16 scroll-mt-4" aria-labelledby="apply-heading">
        <div className="max-w-2xl mx-auto">
          <p className="text-[10px] font-black tracking-[0.25em] text-gray-500 uppercase mb-6">
            For psychologists · Apply to practice
          </p>
          <h2 id="apply-heading" className="scroll-mt-6 text-3xl sm:text-4xl font-black text-gray-900 leading-tight mb-4">
            Join as a <em style={{ fontFamily: "'Playfair Display', serif" }}>psychologist.</em>
          </h2>
          <p className="text-gray-600 text-base leading-relaxed mb-8 max-w-md">
            Licensed clinician? Apply here in four short steps. An admin reviews your details before
            your account is activated.
          </p>

          <TherapistRegisterWizard />

          <p className="text-sm text-gray-500 mt-6">
            Already approved?{' '}
            <Link to={ROUTES.THERAPIST_LOGIN} className="font-semibold text-gray-900 underline underline-offset-2">
              Sign in
            </Link>
          </p>
        </div>
      </section>
    </main>
  </div>
);

export default ClientAppPage;
