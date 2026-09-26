// ============================================================
// MindCare — Help Center "Start here" guide
// Step-by-step onboarding for patients (mobile app) and
// psychologists (website), switchable with tabs.
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Globe, Mail, Smartphone, type LucideIcon } from 'lucide-react';
import { HELP_GUIDES } from '../../constants';
import { cn } from '../../utils/cn';
import type { HelpGuide, HelpGuideStep } from '../../types';

const WHERE_ICON: Record<HelpGuideStep['where'], LucideIcon> = {
  'Mobile app': Smartphone,
  Website: Globe,
  Email: Mail,
};

const GettingStartedGuide: React.FC = () => {
  const [activeId, setActiveId] = useState<HelpGuide['id']>(HELP_GUIDES[0].id);
  const guide = HELP_GUIDES.find((g) => g.id === activeId) ?? HELP_GUIDES[0];

  return (
    <section aria-labelledby="start-here-heading" className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6 sm:p-10">
      <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-2">Start here</p>
      <h2 id="start-here-heading" className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight mb-6">
        New to <span className="italic font-serif font-normal">MindCare?</span>
      </h2>

      {/* Who are you? */}
      <div role="tablist" aria-label="Choose your guide" className="grid grid-cols-2 w-full sm:inline-grid sm:w-auto gap-1 rounded-full bg-[#F3EEE6] p-1 mb-6">
        {HELP_GUIDES.map((g) => (
          <button
            key={g.id}
            type="button"
            role="tab"
            id={`guide-tab-${g.id}`}
            aria-selected={g.id === activeId}
            aria-controls={`guide-panel-${g.id}`}
            onClick={() => setActiveId(g.id)}
            className={cn(
              'px-3 sm:px-5 py-2 rounded-full text-sm font-semibold whitespace-nowrap transition-colors',
              g.id === activeId ? 'bg-gray-900 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900'
            )}
          >
            {g.tab}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={guide.id}
          id={`guide-panel-${guide.id}`}
          role="tabpanel"
          aria-labelledby={`guide-tab-${guide.id}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
        >
          <p className="text-gray-600 mb-8">{guide.intro}</p>

          <ol className="relative">
            {guide.steps.map((step, i) => {
              const WhereIcon = WHERE_ICON[step.where];
              const last = i === guide.steps.length - 1;
              return (
                <li key={step.id} className="relative flex gap-4 sm:gap-6 pb-8 last:pb-0">
                  {/* Number + connecting line */}
                  <div className="flex flex-col items-center shrink-0">
                    <span className="w-9 h-9 rounded-full bg-gray-900 text-white text-sm font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    {!last && <span className="w-px flex-1 bg-gray-200 mt-2" aria-hidden="true" />}
                  </div>

                  <div className="min-w-0 pt-1">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1.5">
                      <h3 className="font-bold text-gray-900">{step.title}</h3>
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#F3EEE6] px-2.5 py-0.5 text-[11px] font-semibold text-gray-600">
                        <WhereIcon size={11} aria-hidden="true" />
                        {step.where}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 leading-relaxed max-w-2xl">{step.body}</p>
                    {step.link && (
                      <Link
                        to={step.link.to}
                        className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-gray-900 underline underline-offset-4 decoration-gray-300 hover:decoration-gray-900"
                      >
                        {step.link.label} <ArrowRight size={14} aria-hidden="true" />
                      </Link>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </motion.div>
      </AnimatePresence>
    </section>
  );
};

export default GettingStartedGuide;
