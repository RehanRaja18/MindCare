// ============================================================
// MindCare — Navbar Component
// ============================================================

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Logo from '../common/Logo';
import Button from '../common/Button';
import { NAV_ITEMS, ROUTES } from '../../constants';
import { useScrollPosition } from '../../hooks/useScrollPosition';
import { cn } from '../../utils/cn';

interface NavLink {
  label: string;
  to: string;
}

interface NavbarProps {
  /** Main button on the right. Defaults to "Get started" (app download + sign-up). */
  cta?: NavLink;
  /** Optional quieter link shown before the button (e.g. "Sign in"). */
  secondary?: NavLink;
}

const DEFAULT_CTA: NavLink = { label: 'Get started →', to: ROUTES.CLIENT_APP };

const Navbar: React.FC<NavbarProps> = ({ cta = DEFAULT_CTA, secondary }) => {
  const scrollY = useScrollPosition();
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrolled = scrollY > 20;

  return (
    <header
      role="banner"
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-[#F5F0E8]/95 backdrop-blur-md shadow-sm border-b border-gray-200/60'
          : 'bg-transparent'
      )}
    >
      <nav
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Logo />

        {/* Desktop Nav */}
        <ul className="hidden lg:flex items-center gap-1" role="list">
          {NAV_ITEMS.map((item) => (
            <li key={item.label}>
              {item.href.startsWith('/') ? (
                <Link
                  to={item.href}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors rounded-lg hover:bg-gray-100/60"
                >
                  {item.label}
                </Link>

              ) : (
                <a 
                  href={item.href}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors rounded-lg hover:bg-gray-100/60"
                >
                {item.label}
                </a>
              )}
            </li>
          ))}
        </ul>

        {/* Right side */}
        <div className="hidden lg:flex items-center gap-3">
          {secondary && (
            <Link to={secondary.to} className="px-3 py-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors">
              {secondary.label}
            </Link>
          )}
          <Link to={cta.to}>
            <Button size="sm" variant="primary" className="rounded-full px-5">
              {cta.label}
            </Button>
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <button
          className="lg:hidden p-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
          onClick={() => setMobileOpen((v) => !v)}
          aria-expanded={mobileOpen}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
     </nav>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="lg:hidden bg-[#F5F0E8]/98 border-t border-gray-200 px-4 pb-6">
          <ul className="flex flex-col gap-1 mt-3" role="list">
            {NAV_ITEMS.map((item) => (
              <li key={item.label}>
                {item.href.startsWith('/') ? (
                  <Link
                    to={item.href}
                    onClick={() => setMobileOpen(false)}
                    className="block px-3 py-3 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <a
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className="block px-3 py-3 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    {item.label}
                  </a>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-col gap-3">
            <Link to={cta.to} onClick={() => setMobileOpen(false)}>
              <Button variant="primary" fullWidth size="md">
                {cta.label}
              </Button>
            </Link>
            {secondary && (
              <Link to={secondary.to} onClick={() => setMobileOpen(false)}>
                <Button variant="secondary" fullWidth size="md">
                  {secondary.label}
                </Button>
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;