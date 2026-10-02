// ============================================================
// MindCare — Reference lists from the backend
// GET /reference/specializations/ → [{ slug, name }]
// GET /reference/languages/       → [{ code, name }]
// GET /reference/countries/       → [{ code, name }]
// Public, unauthenticated endpoints. The register API only accepts
// values from these lists, so the live list wins; the bundled fallback
// is used only until it loads or if the request fails.
// ============================================================

import { useEffect, useState } from 'react';
import { getReferenceList } from '../services/api.service';
import type { Option } from '../utils/locale';

export type ReferenceKind = 'specializations' | 'languages' | 'countries';

const cache = new Map<ReferenceKind, Promise<Option[] | null>>();

function load(kind: ReferenceKind): Promise<Option[] | null> {
  if (!cache.has(kind)) {
    const p = getReferenceList(kind).then((rows) => {
      if (!rows?.length) {
        cache.delete(kind); // let a later mount retry
        return null;
      }
      return rows;
    });
    cache.set(kind, p);
  }
  return cache.get(kind)!;
}

/** Live options for a reference list, falling back to `fallback`. */
export function useReferenceOptions(kind: ReferenceKind, fallback: Option[], sort?: (a: Option[]) => Option[]) {
  const [options, setOptions] = useState<Option[]>(fallback);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    load(kind).then((rows) => {
      if (active && rows) {
        setOptions(sort ? sort(rows) : rows);
        setLive(true);
      }
    });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  return { options, live };
}
