// ============================================================
// MindCare — Pricing Page ("One price. No surprises.")
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import { Check, Heart, Shield, Code, type LucideIcon } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import Button from '../components/common/Button';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import { ROUTES, PRICING_PLAN, PRICING_FEATURE_STRIPS } from '../constants';
import type { PricingFeatureStrip } from '../types';

const ICON_MAP: Record<PricingFeatureStrip['icon'], LucideIcon> = {
  heart: Heart,
  shield: Shield,
  code: Code,
};

const PricingPage: React.FC = () => {
  return (
    <div className="min-h-screen mc-page-glow flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 pt-32 pb-16 text-center w-full">
        <Reveal>
          <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">
            Honest pricing · Cancel any time
          </p>

          <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-6">
            One price. <span className="italic font-serif font-normal">No surprises.</span>
          </h1>

          <p className="text-gray-500 text-lg mb-16">
            Trial 7 days, no card · NGO scholarships available
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-10 text-left max-w-md mx-auto mb-16">
            <p className="text-xs font-semibold tracking-widest text-orange-600 uppercase mb-2">{PRICING_PLAN.name}</p>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-5xl font-black text-gray-900">{PRICING_PLAN.price}</span>
              <span className="text-gray-500">{PRICING_PLAN.period}</span>
            </div>
            <p className="text-sm text-gray-500 mb-8">{PRICING_PLAN.trial}</p>

            <ul className="space-y-3 mb-8">
              {PRICING_PLAN.features.map((feature) => (
                <li key={feature} className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
                    <Check size={12} aria-hidden="true" />
                  </span>
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>

            <Link to={ROUTES.CLIENT_APP}>
              <Button variant="primary" size="lg" fullWidth>
                Start free trial →
              </Button>
            </Link>
          </div>
        </Reveal>
      </main>

      <RevealGroup className="max-w-5xl mx-auto w-full px-4 sm:px-6 pb-16 grid grid-cols-1 sm:grid-cols-3 gap-4" stagger={0.1}>
        {PRICING_FEATURE_STRIPS.map((strip) => {
          const Icon = ICON_MAP[strip.icon];
          return (
            <RevealItem key={strip.id}>
              <div className="bg-[#EFE9DF] rounded-2xl p-6 flex items-start gap-4 h-full">
                <span className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-gray-700 shrink-0">
                  <Icon size={16} aria-hidden="true" />
                </span>
                <div>
                  <p className="font-bold text-gray-900 mb-1">{strip.title}</p>
                  <p className="text-sm text-gray-600 leading-relaxed">{strip.description}</p>
                </div>
              </div>
            </RevealItem>
          );
        })}
      </RevealGroup>

      <Footer />
    </div>
  );
};

export default PricingPage;