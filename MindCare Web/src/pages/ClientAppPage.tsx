// ============================================================
// MindCare — Screen 3: Client App Download Page
// "MindCare lives in your pocket."
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail } from 'lucide-react';
import Logo from '../components/common/Logo';
import PhoneMockup from '../components/mockup/PhoneMockup';
import QRCode from '../components/mockup/QRCode';
import Button from '../components/common/Button';
import Reveal from '../components/motion/Reveal';
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
    <header className="flex items-center justify-between px-6 sm:px-10 py-5 border-b border-gray-200/60">
      <Logo />
      <Link
        to={ROUTES.HOME}
        className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
      >
        ← Back to home
      </Link>
    </header>

    {/* Split layout */}
    <main className="flex-1 grid md:grid-cols-2">
      {/* Left: Copy */}
      <Reveal className="flex flex-col justify-center px-8 sm:px-14 py-16 max-w-xl" y={16}>
        {/* Step badge */}
        <p className="text-[10px] font-black tracking-[0.25em] text-gray-500 uppercase mb-6">
          Get the app
        </p>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl font-black text-gray-900 leading-tight mb-6">
          MindCare lives in{' '}
          <em style={{ fontFamily: "'Playfair Display', serif" }}>your pocket.</em>
        </h1>

        {/* Body copy */}
        <p className="text-gray-600 text-base leading-relaxed mb-4 max-w-sm">
          The client side of MindCare is built for mobile — body sensors, daily
          check-ins, voice journaling and quiet circles are easier to live with on a
          phone than on a laptop.
        </p>
        <p className="text-gray-500 text-sm leading-relaxed mb-10 max-w-sm">
          Download the app, finish your intake, and your first session can be booked
          tonight.
        </p>

        {/* Store buttons */}
        <div className="flex flex-wrap gap-3 mb-10">
          <StoreButton platform="google" />
          <StoreButton platform="apple" />
        </div>

        {/* QR row */}
        <div className="flex items-center gap-5 mb-8">
          <QRCode className="w-24 h-24 shrink-0" />
          <div>
            <p className="font-bold text-gray-900 text-base">Or point your camera here.</p>
            <p className="text-sm text-gray-500 mt-1">
              Detects your device · takes you to the right store.
            </p>
          </div>
        </div>

        {/* Email link */}
        <div>
          <p className="text-xs text-gray-500 mb-1">
            iOS 15+ · Android 9+ &nbsp;·&nbsp; Free · 7-day trial
          </p>
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
      </Reveal>

      {/* Right: Phone mockup */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 }}
        className="hidden md:flex items-center justify-center bg-[#EDEAE0] px-10 py-16"
      >
        <PhoneMockup />
      </motion.div>
    </main>
  </div>
);

export default ClientAppPage;
