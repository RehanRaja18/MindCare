// ============================================================
// MindCare — ScrollManager
// One place that decides where the page is scrolled:
//  • Opening / reloading the site always starts at the top, even if the
//    address still ends in an old "#section" from a previous visit.
//  • Changing page opens the new page at the top (not wherever the last
//    page was scrolled to).
//  • In-app links to a section (e.g. "/#how-it-works") scroll to it, then
//    drop the "#…" from the address so it isn't remembered for next time.
// ============================================================

import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

const clearHashFromAddress = () => {
  const { pathname, search } = window.location;
  window.history.replaceState(window.history.state, '', pathname + search);
};

const ScrollManager = () => {
  const { pathname, hash, key } = useLocation();

  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';
  }, []);

  useLayoutEffect(() => {
    // React Router gives the page-load location the key "default"
    const firstLoad = key === 'default';

    if (!hash || firstLoad) {
      if (hash) clearHashFromAddress();
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      return;
    }

    // The target page may still be lazy-loading, so look for the section
    // for a short while before giving up.
    const id = decodeURIComponent(hash.slice(1));
    let tries = 0;
    let timer: number | undefined;
    const find = () => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        clearHashFromAddress();
      } else if (++tries < 40) {
        timer = window.setTimeout(find, 50);
      } else {
        clearHashFromAddress();
      }
    };
    find();
    return () => window.clearTimeout(timer);
  }, [pathname, hash, key]);

  return null;
};

export default ScrollManager;
