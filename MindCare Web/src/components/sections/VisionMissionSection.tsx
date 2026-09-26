// ============================================================
// MindCare — Vision / Mission / Promise Dark Section
// ============================================================

import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { HERO_STATS } from '../../constants';
import Reveal from '../motion/Reveal';
import AnimatedCounter from '../motion/AnimatedCounter';
import { usePlatformStats } from '../../hooks/usePlatformStats';

const promises = [
  'A real, verified human at the center of every plan.',
  'Your data is yours. Always.',
  'No predatory ads, no growth-hack notifications.',
  "If you can't afford it, our NGO partners can.",
];

const VisionMissionSection: React.FC = () => {
  const stats = usePlatformStats();
  return (
  <section
    className="bg-gray-900 text-white py-24"
    aria-label="Vision, mission and our promise"
  >
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid md:grid-cols-3 gap-12">
        {/* Vision */}
        <Reveal>
          <p className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-gray-500 uppercase mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400" aria-hidden="true" />
            Vision
          </p>
          <h2 className="text-3xl font-black leading-tight">
            That every person has access to{' '}
            <em style={{ fontFamily: "'Playfair Display', serif" }}>good,</em>
            <br />
            <em style={{ fontFamily: "'Playfair Display', serif" }}>held</em> mental care.
          </h2>
        </Reveal>

        {/* Mission */}
        <Reveal delay={0.1}>
          <p className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-gray-500 uppercase mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
            Mission
          </p>
          <p className="text-gray-300 text-sm leading-relaxed mb-8">
            To make weekly therapy normal, affordable, and accountable — and to use
            technology to{' '}
            <strong className="text-white">extend the therapist's hand</strong> into the
            rest of the week, not replace it.
          </p>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            {HERO_STATS.map((s) => (
              <div key={s.label}>
                <p className="text-2xl font-black text-white">
                  <AnimatedCounter value={stats[s.key].toLocaleString('en-US')} />
                </p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </Reveal>

        {/* Promise */}
        <Reveal delay={0.2}>
          <p className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-gray-500 uppercase mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" aria-hidden="true" />
            Our Promise
          </p>
          <motion.ul
            className="space-y-3"
            role="list"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }}
          >
            {promises.map((p) => (
              <motion.li
                key={p}
                className="flex items-start gap-3 text-sm text-gray-300"
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
                }}
              >
                <Check size={14} className="shrink-0 mt-0.5 text-emerald-400" aria-hidden="true" />
                {p}
              </motion.li>
            ))}
          </motion.ul>
        </Reveal>
      </div>
    </div>
  </section>
);
};

export default VisionMissionSection;
