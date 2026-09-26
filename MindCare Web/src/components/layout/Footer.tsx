// ============================================================
// MindCare — Footer Component
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../common/Logo';
import { ROUTES } from '../../constants';

interface FooterLink {
  label: string;
  to: string;
}

const PLATFORM_LINKS: FooterLink[] = [
  { label: 'How it works', to: '/#how-it-works' },
  { label: 'For therapists', to: ROUTES.FOR_THERAPISTS },
  { label: 'For NGOs', to: ROUTES.FOR_NGOS },
  { label: 'Pricing', to: ROUTES.PRICING },
  { label: 'Stories', to: ROUTES.STORIES },
];

const COMPANY_LINKS: FooterLink[] = [
  { label: 'About us', to: ROUTES.ABOUT_US },
  { label: 'Help', to: ROUTES.HELP },
];

const LEGAL_LINKS: FooterLink[] = [
  { label: 'Privacy Policy', to: ROUTES.PRIVACY },
  { label: 'Terms of Service', to: ROUTES.TERMS },
  { label: 'HIPAA Alignment', to: ROUTES.HIPAA },
  { label: 'Cookie Policy', to: ROUTES.COOKIES },
];

const Footer: React.FC = () => (
  <footer className="bg-gray-900 text-gray-400 pt-16 pb-10" role="contentinfo">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
        {/* Brand */}
        <div className="md:col-span-1">
          <Logo className="text-white" onDark />
          <p className="mt-4 text-sm leading-relaxed">
            Weekly therapy, AI co-pilot, and the days between — all in one place.
          </p>
          <p className="mt-4 text-xs text-gray-600">© {new Date().getFullYear()} MindCare. All rights reserved.</p>
        </div>

        {/* Platform */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-4 uppercase tracking-widest">Platform</h3>
          <ul className="space-y-2 text-sm">
            {PLATFORM_LINKS.map((l) => (
              <li key={l.label}>
                <Link to={l.to} className="hover:text-white transition-colors">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Company */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-4 uppercase tracking-widest">Company</h3>
          <ul className="space-y-2 text-sm">
            {COMPANY_LINKS.map((l) => (
              <li key={l.label}>
                <Link to={l.to} className="hover:text-white transition-colors">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Legal */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-4 uppercase tracking-widest">Legal</h3>
          <ul className="space-y-2 text-sm">
            {LEGAL_LINKS.map((l) => (
              <li key={l.label}>
                <Link to={l.to} className="hover:text-white transition-colors">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-gray-800 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-600">
        <p>PMDC-verified therapists · Umang · Rozan partner · HIPAA-aligned</p>
        <div className="flex gap-4">
          <Link to={ROUTES.CLIENT_APP} className="hover:text-gray-400 transition-colors">Get started</Link>
        </div>
      </div>
    </div>
  </footer>
);

export default Footer;
