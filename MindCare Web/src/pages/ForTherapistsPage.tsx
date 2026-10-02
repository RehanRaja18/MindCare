// ============================================================
// MindCare — For Therapists Page ("Spend your hour on the person.")
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import { Code, Calendar, FileText, Heart, Shield, type LucideIcon } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Button from '../components/common/Button';
import Avatar from '../components/common/Avatar';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import { ROUTES, THERAPIST_FEATURES, THERAPIST_STATS, THERAPIST_TESTIMONIAL } from '../constants';
import type { TherapistFeature } from '../types';

const ICON_MAP: Record<TherapistFeature['icon'], LucideIcon> = {
  code: Code,
  calendar: Calendar,
  'file-text': FileText,
  heart: Heart,
  shield: Shield,
};

const ForTherapistsPage: React.FC = () => {
  return (
    <div className="min-h-screen mc-page-glow">
      {/* This page is for psychologists only: no app-download "Get started" here. */}
      <Navbar
        cta={{ label: 'Apply to practice →', to: ROUTES.THERAPIST_REGISTER }}
        secondary={{ label: 'Sign in', to: ROUTES.THERAPIST_LOGIN }}
      />

      <main className="pt-16 grid grid-cols-1 lg:grid-cols-2">
        {/* Left — pitch */}
        <div className="px-4 sm:px-6 lg:px-16 pt-24 pb-24">
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">
              For Therapists
            </p>

            <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-8">
              Spend your <span className="italic font-serif font-normal">hour</span>
              <br />
              on the <span className="italic font-serif font-normal">person.</span>
            </h1>

            <p className="text-gray-600 text-lg leading-relaxed max-w-xl mb-10">
              MindCare handles the rest — booking, billing, notes, between-session messaging, and a
              co-pilot named Aida you can shape per patient. You stay in charge. We stay in the back
              office.
            </p>

            <div className="flex flex-wrap gap-4 mb-14">
              <Link to={ROUTES.THERAPIST_REGISTER}>
                <Button variant="primary" size="lg">
                  Apply to practice →
                </Button>
              </Link>
              <Link to={ROUTES.THERAPIST_LOGIN}>
                <Button variant="secondary" size="lg">
                  Sign in
                </Button>
              </Link>
              <Button variant="secondary" size="lg">
                Read the clinical model
              </Button>
            </div>
          </Reveal>

          <RevealGroup className="flex flex-wrap gap-x-12 gap-y-6" stagger={0.08}>
            {THERAPIST_STATS.map((stat) => (
              <RevealItem key={stat.label}>
                <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-500">{stat.label}</p>
              </RevealItem>
            ))}
          </RevealGroup>
        </div>

        {/* Right — feature list */}
        <div className="px-4 sm:px-6 lg:px-16 pt-24 pb-24 bg-[#EFE9DF]">
          <RevealGroup className="space-y-4" stagger={0.1}>
            {THERAPIST_FEATURES.map((feature) => {
              const Icon = ICON_MAP[feature.icon];
              return (
                <RevealItem key={feature.id}>
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-start gap-4">
                    <span
                      className={`w-11 h-11 rounded-xl flex items-center justify-center text-white shrink-0 ${feature.color}`}
                    >
                      <Icon size={20} aria-hidden="true" />
                    </span>
                    <div>
                      <p className="font-bold text-gray-900 mb-1">{feature.title}</p>
                      <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
                    </div>
                  </div>
                </RevealItem>
              );
            })}

            {/* Testimonial */}
            <RevealItem>
              <div className="bg-gray-900 rounded-2xl p-6 flex items-start gap-4 mt-6">
                <Avatar initials={THERAPIST_TESTIMONIAL.initials} color="bg-rose-400" />
                <p className="text-white text-sm leading-relaxed">
                  &ldquo;{THERAPIST_TESTIMONIAL.quote}&rdquo;{' '}
                  <span className="text-gray-400">
                    — {THERAPIST_TESTIMONIAL.name}, {THERAPIST_TESTIMONIAL.meta}
                  </span>
                </p>
              </div>
            </RevealItem>
          </RevealGroup>
        </div>
      </main>
    </div>
  );
};

export default ForTherapistsPage;