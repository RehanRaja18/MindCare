// ============================================================
// MindCare — Partners Marquee Section
// ============================================================

import React from 'react';
import { PARTNERS } from '../../constants';

const TINTS = [
  'bg-orange-50 border-orange-100 text-orange-700',
  'bg-emerald-50 border-emerald-100 text-emerald-700',
  'bg-rose-50 border-rose-100 text-rose-700',
  'bg-purple-50 border-purple-100 text-purple-700',
];

const PartnersSection: React.FC = () => (
  <section
    className="border-t border-b border-gray-200 py-10"
    aria-label="Partners"
  >
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row items-center gap-8 sm:gap-16">
        <p className="text-xs font-bold tracking-[0.2em] text-gray-500 uppercase whitespace-nowrap shrink-0">
          Partners
        </p>

        <div
          className="group relative w-full min-w-0 flex-1 overflow-hidden py-3 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]"
        >
          <div className="flex w-max gap-6 sm:gap-8 animate-marquee group-hover:[animation-play-state:paused]">
            {[...PARTNERS, ...PARTNERS].map((p, i) => (
              <div
                key={`${p.name}-${i}`}
                className={`floating-card px-5 py-2.5 rounded-full border shadow-sm font-semibold text-sm tracking-wide whitespace-nowrap cursor-default hover:shadow-md hover:-translate-y-0.5 transition-shadow ${
                  TINTS[i % TINTS.length]
                }`}
                style={{ animationDelay: `${(i % PARTNERS.length) * 0.35}s` }}
              >
                {p.name}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default PartnersSection;
