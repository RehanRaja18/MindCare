// ============================================================
// MindCare — Hero Section (Screen 1)
// ============================================================

import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, type Variants } from 'framer-motion';
import { Shield, Heart, Lock, Stethoscope } from 'lucide-react';
import Button from '../common/Button';
import { ROUTES } from '../../constants';
import { RevealGroup, RevealItem } from '../motion/Reveal';

// ——— Headline word-stagger: each phrase swings and focuses into place ———
const headlineContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.13, delayChildren: 0.15 } },
};

const headlineWord: Variants = {
  hidden: { opacity: 0, y: 34, scale: 0.88, rotate: -3, filter: 'blur(12px)' },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    rotate: 0,
    filter: 'blur(0px)',
    transition: { duration: 0.75, ease: [0.22, 1, 0.36, 1] },
  },
};

// ——— Floating appointment card ———
const AppointmentCard: React.FC = () => (
  <motion.div
    initial={{ opacity: 0, y: 16, scale: 0.95 }}
    animate={{ opacity: 1, y: [0, -8, 0], scale: 1 }}
    transition={{
      opacity: { duration: 0.6, delay: 0.5 },
      scale: { duration: 0.6, delay: 0.5 },
      y: { duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1.1 },
    }}
    className="absolute top-3 right-3 sm:top-8 sm:right-0 bg-gray-900 text-white rounded-2xl px-4 py-3 sm:px-5 sm:py-4 shadow-2xl sm:min-w-[220px] z-10"
  >
    <p className="text-[10px] font-semibold tracking-widest text-gray-400 uppercase mb-2 sm:mb-3">
      Next · Today 5 PM
    </p>
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-gradient-to-br from-orange-400 to-rose-400 flex items-center justify-center shrink-0">
        <Stethoscope size={16} className="text-white" aria-hidden="true" />
      </div>
      <div>
        <p className="font-semibold text-sm">Your Therapist</p>
        <p className="text-gray-400 text-xs">Anxiety · 50 min</p>
      </div>
    </div>
  </motion.div>
);

// ——— Mood mini-card ———
const MoodCard: React.FC = () => (
  <motion.div
    initial={{ opacity: 0, y: -16, scale: 0.95 }}
    animate={{ opacity: 1, y: [0, 8, 0], scale: 1 }}
    transition={{
      opacity: { duration: 0.6, delay: 0.7 },
      scale: { duration: 0.6, delay: 0.7 },
      y: { duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1.3 },
    }}
    className="absolute bottom-3 left-3 sm:left-auto sm:bottom-0 sm:right-8 bg-white rounded-2xl px-4 py-3 sm:px-5 sm:py-4 shadow-xl border border-gray-100 w-[170px] sm:w-auto sm:min-w-[200px] z-10"
  >
    <p className="text-[10px] font-semibold tracking-widest text-gray-500 uppercase mb-2">
      Mood · 14 Days
    </p>
    {/* Tiny SVG sparkline */}
    <svg viewBox="0 0 120 30" className="w-full h-6 sm:h-8" aria-hidden="true">
      <polyline
        points="0,20 20,18 40,22 60,14 80,16 100,10 120,12"
        fill="none"
        stroke="#10B981"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
    <div className="flex items-center justify-between mt-2">
      <span className="text-[10px] text-gray-400">2 weeks ago</span>
      <span className="text-[10px] font-semibold text-emerald-600">↑ steady</span>
    </div>
  </motion.div>
);

// ——— Hero avatar group (dummy users) ———
const AvatarGroup: React.FC = () => {
  const colors = ['bg-orange-400', 'bg-emerald-400', 'bg-purple-400', 'bg-blue-400'];
  const labels = ['L', 'A', 'H', 'O'];
  return (
    <div className="flex items-center gap-2">
      <div className="flex -space-x-2">
        {colors.map((c, i) => (
          <div
            key={i}
            className={`w-8 h-8 rounded-full border-2 border-[#F5F0E8] ${c} flex items-center justify-center text-white text-xs font-bold`}
            aria-hidden="true"
          >
            {labels[i]}
          </div>
        ))}
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-900">12,400+</p>
        <p className="text-[10px] text-gray-500">walking the path · 14 cities</p>
      </div>
    </div>
  );
};

// ——— Trust badges ———
const TrustBadges: React.FC = () => (
  <div className="flex flex-wrap gap-6 mt-6">
    {[
      { icon: <Shield size={14} />, text: 'PMDC-verified therapists' },
      { icon: <Heart size={14} />, text: 'Umang · Rozan partner' },
      { icon: <Lock size={14} />, text: 'HIPAA-aligned' },
    ].map(({ icon, text }) => (
      <div key={text} className="flex items-center gap-2 text-xs text-gray-500">
        <span className="text-gray-400">{icon}</span>
        <span>{text}</span>
      </div>
    ))}
  </div>
);

// ——— Looping meditation clip, standing in for "the work" ———
// React sets `muted` only as a property (never the attribute), which mobile
// autoplay policies can reject — so set both and start playback ourselves,
// retrying on the first touch/scroll or when the tab becomes visible again.
function useMobileSafeAutoplay() {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    video.muted = true;
    video.setAttribute('muted', '');

    const tryPlay = () => {
      if (video.paused) video.play().catch(() => {});
    };
    const onVisible = () => document.visibilityState === 'visible' && tryPlay();

    tryPlay();
    video.addEventListener('canplay', tryPlay);
    window.addEventListener('touchstart', tryPlay, { passive: true });
    window.addEventListener('scroll', tryPlay, { passive: true });
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      video.removeEventListener('canplay', tryPlay);
      window.removeEventListener('touchstart', tryPlay);
      window.removeEventListener('scroll', tryPlay);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  return ref;
}

const HeroVisualBackdrop: React.FC = () => {
  const videoRef = useMobileSafeAutoplay();
  return (
  <div className="relative w-full h-full" aria-hidden="true">
    <div className="absolute inset-0 bg-gray-900 rounded-3xl overflow-hidden">
      {/* Short looping clip — poster shows instantly, video fades in once it can play */}
      <video
        ref={videoRef}
        autoPlay
        preload="auto"
        muted
        loop
        playsInline
        poster="https://images.unsplash.com/photo-1519834785169-98be25ec3f84?q=80&w=1200&auto=format&fit=crop"
        className="absolute inset-0 w-full h-full object-cover opacity-80"
      >
        <source src="https://assets.mixkit.co/videos/15715/15715-360.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/30 to-gray-900/10" />
      {/* Breathing blobs */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-gradient-to-br from-orange-300/25 to-rose-400/30 blur-2xl animate-breathe" />
      <div
        className="absolute top-8 left-8 w-32 h-32 rounded-full bg-gradient-to-br from-orange-400/20 to-amber-300/10 blur-xl animate-breathe"
        style={{ animationDelay: '1.5s' }}
      />
    </div>
  </div>
  );
};

// ——— "Walking the path": a couple of small figures travelling a winding
// route across the hero, echoing the "12,400+ walking the path" copy. Real
// motion, not just a color shift — built in plain SVG/CSS, on-theme color. ———
const PATH_D = 'M -40 300 Q 220 120 460 240 T 900 160';

const WalkerIcon: React.FC<{ className?: string; delay: string; duration: string }> = ({
  className,
  delay,
  duration,
}) => (
  <div
    className={`walker absolute ${className ?? ''}`}
    style={{
      offsetPath: `path('${PATH_D}')`,
      animationDelay: delay,
      animationDuration: duration,
    } as React.CSSProperties}
  >
    <svg width="22" height="30" viewBox="0 0 20 28" fill="none">
      <circle cx="10" cy="4" r="4" fill="currentColor" />
      <path
        d="M10 8 L10 18 M10 12 L4 16 M10 12 L16 16 M10 18 L5 27 M10 18 L15 27"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  </div>
);

const WalkingPathMotif: React.FC = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
    <svg className="absolute inset-0 w-full h-full opacity-30" viewBox="0 0 900 400" preserveAspectRatio="none">
      <path d={PATH_D} fill="none" stroke="#c48a5a" strokeWidth="2" strokeDasharray="2 10" strokeLinecap="round" />
    </svg>
    <WalkerIcon className="text-orange-500/70" delay="0s" duration="16s" />
    <WalkerIcon className="text-rose-500/60" delay="7s" duration="16s" />
  </div>
);

// ——— Main Hero Section ———
const HeroSection: React.FC = () => (
  <section
    className="relative min-h-screen pt-24 pb-16 overflow-hidden"
    aria-labelledby="hero-heading"
  >
    <WalkingPathMotif />
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Eyebrow */}
      <RevealItem>
        <p className="text-xs font-semibold tracking-[0.2em] text-gray-500 uppercase mb-8">
          Mental Care · Weekly · Since 2024
        </p>
      </RevealItem>

      <div className="grid lg:grid-cols-2 gap-10 lg:gap-12 items-center">
        {/* Left: Copy */}
        <RevealGroup stagger={0.12}>
          <motion.h1
            id="hero-heading"
            className="text-[2.75rem] sm:text-6xl xl:text-7xl font-black text-gray-900 leading-[1.05] tracking-tight mb-8"
            style={{ fontFamily: "'Inter', sans-serif" }}
            initial="hidden"
            animate="visible"
            variants={headlineContainer}
          >
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '0s' }}>
                A quieter
              </span>
            </motion.span>{' '}
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '0.3s' }}>
                <em
                  className="not-italic italic bg-[length:200%_auto] animate-text-shimmer bg-gradient-to-r from-orange-500 via-rose-500 to-purple-500 bg-clip-text text-transparent"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  mind
                </em>
              </span>
            </motion.span>
            <br />
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '0.6s' }}>
                is the work
              </span>
            </motion.span>
            <br />
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '0.9s' }}>
                of
              </span>
            </motion.span>{' '}
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '1.2s' }}>
                <em
                  className="bg-[length:200%_auto] animate-text-shimmer bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  a year
                </em>
              </span>
            </motion.span>
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '1.5s' }}>
                , not
              </span>
            </motion.span>
            <br />
            <motion.span variants={headlineWord} className="inline-block">
              <span className="inline-block floating-text" style={{ animationDelay: '1.8s' }}>
                a download.
              </span>
            </motion.span>
          </motion.h1>

          <RevealItem>
            <p className="text-gray-600 text-base sm:text-lg leading-relaxed max-w-md mb-10">
              MindCare pairs you with a verified therapist, supports you between sessions
              with an AI co-pilot they shape, and walks the year with you. Body data,
              journaling, peer circles — held by humans, not just an app.
            </p>
          </RevealItem>

          {/* CTA row */}
          <RevealItem>
            <div className="flex flex-wrap items-center gap-4 mb-8">
              <Link to={ROUTES.CLIENT_APP}>
                <Button size="lg" variant="primary" className="rounded-full font-bold">
                  Get started →
                </Button>
              </Link>
              <a
                href="#watch"
                className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors"
              >
                <span className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center">
                  ▶
                </span>
                Watch · 90 seconds
              </a>
              <AvatarGroup />
            </div>
          </RevealItem>

          <RevealItem>
            <TrustBadges />
          </RevealItem>
        </RevealGroup>

        {/* Right: Visual card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="relative h-[340px] sm:h-96 lg:h-[520px]"
        >
          <div className="absolute inset-0 lg:inset-8">
            <HeroVisualBackdrop />
          </div>
          <AppointmentCard />
          <MoodCard />
        </motion.div>
      </div>
    </div>
  </section>
);

export default HeroSection;
