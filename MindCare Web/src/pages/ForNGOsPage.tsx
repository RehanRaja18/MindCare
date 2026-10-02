// ============================================================
// MindCare — For NGOs Page ("The line we hand people to.")
// ============================================================

import React from 'react';
import Navbar from '../components/layout/Navbar';
import Avatar from '../components/common/Avatar';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import NgoRegisterForm from '../components/ngo/NgoRegisterForm';
import { NGO_PARTNERS, NGO_STATS } from '../constants';

const ForNGOsPage: React.FC = () => {
  return (
    <div className="min-h-screen mc-page-glow">
      <Navbar />

      <main className="pt-16 grid grid-cols-1 lg:grid-cols-2">
        {/* Left — pitch + register form */}
        <div className="px-4 sm:px-6 lg:px-16 pt-16 pb-24">
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">
              For NGO Partners
            </p>

            <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-8">
              The line we hand people <span className="italic font-serif font-normal">to.</span>
            </h1>

            <p className="text-gray-600 text-lg leading-relaxed max-w-xl mb-10">
              When MindCare can&apos;t be enough — late-night crises, sliding-scale care, hospital
              escalation — we route to verified NGO partners. No dashboard, no app to learn. Just a
              call, a handover, a closed loop.
            </p>
          </Reveal>

          <RevealGroup className="flex flex-wrap gap-x-12 gap-y-6 mb-12" stagger={0.08}>
            {NGO_STATS.map((stat) => (
              <RevealItem key={stat.label}>
                <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-500">{stat.label}</p>
              </RevealItem>
            ))}
          </RevealGroup>

          <Reveal delay={0.1}>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 max-w-2xl">
            <h2 className="text-xs font-bold tracking-widest text-gray-900 uppercase mb-5">
              Register your NGO
            </h2>

            <NgoRegisterForm />
          </div>
          </Reveal>
        </div>

        {/* Right — current partners (dark panel) */}
        <div className="bg-gray-900 px-4 sm:px-6 lg:px-16 pt-16 pb-24 min-h-[600px]">
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-orange-400 uppercase mb-8">
              Current Partners
            </p>
          </Reveal>

          <RevealGroup className="space-y-4" stagger={0.1}>
            {NGO_PARTNERS.map((partner) => (
              <RevealItem key={partner.id}>
                <div className="bg-gray-800/60 border border-gray-700/60 rounded-2xl p-5 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Avatar initials={partner.initials} color={partner.color} size="lg" />
                    <div>
                      <p className="text-white font-bold">{partner.name}</p>
                      <p className="text-sm text-gray-400">{partner.description}</p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-white font-bold">{partner.routedCount.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">routed</p>
                  </div>
                </div>
              </RevealItem>
            ))}
          </RevealGroup>

          <Reveal delay={0.15}>
            <p className="text-sm text-gray-400 leading-relaxed mt-10">
              Partners receive a closed-loop case report after every routed handoff. No PII unless
              you&apos;ve been added to the case lead.
            </p>
          </Reveal>
        </div>
      </main>
    </div>
  );
};

export default ForNGOsPage;