// ============================================================
// MindCare — Logo Component
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import { ROUTES } from '../../constants';

interface LogoProps {
  className?: string;
  /** Rendered on a dark background — gives the mark a light backing so its dark strokes stay visible. */
  onDark?: boolean;
}

const Logo: React.FC<LogoProps> = ({ className = '', onDark = false }) => (
  <Link
    to={ROUTES.HOME}
    className={`inline-flex items-center gap-2 text-xl font-bold tracking-tight text-gray-900 select-none shrink-0 ${className}`}
    aria-label="MindCare Home"
  >
    <img
      src="/mindcare-mark.png"
      alt=""
      width={32}
      height={32}
      className={'w-8 h-8 object-contain' + (onDark ? ' rounded-full bg-[#F5F0E8] p-0.5' : '')}
      aria-hidden="true"
    />
    <span>
      MindCare
      <span className="text-orange-500">.</span>
    </span>
  </Link>
);

export default Logo;
