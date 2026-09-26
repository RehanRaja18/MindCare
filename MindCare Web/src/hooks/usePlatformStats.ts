// ============================================================
// MindCare — usePlatformStats
// Live public counts (people in care, verified therapists, cities).
// One request per page load, shared by every component that asks.
// ============================================================

import { useEffect, useState } from 'react';
import { EMPTY_PLATFORM_STATS, getPlatformStats } from '../services/api.service';
import type { PlatformStats } from '../types';

let cached: Promise<PlatformStats> | null = null;

export function usePlatformStats(): PlatformStats {
  const [stats, setStats] = useState<PlatformStats>(EMPTY_PLATFORM_STATS);

  useEffect(() => {
    let active = true;
    cached ??= getPlatformStats();
    cached.then((s) => active && setStats(s));
    return () => {
      active = false;
    };
  }, []);

  return stats;
}
