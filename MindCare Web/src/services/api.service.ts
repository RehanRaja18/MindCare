// ============================================================
// MindCare — API Service Layer
// All HTTP calls live here. Swap dummy data for real endpoints.
// ============================================================

import { API_BASE_URL } from '../constants';
import { getAccessToken, getRefreshToken, isExpired, saveTokens } from './tokens';
import type {
  RegisterPayload,
  RegisteredUser,
  ApiResponse,
  StoryEntry,
  StorySubmission,
  ContactMessage,
  PlatformStats,
} from '../types';

// ——— Generic fetch wrapper ———
// Auth is a Bearer JWT (no cookies), so requests go without credentials —
// the backend's CORS config (CORS_ALLOW_CREDENTIALS = False) requires that.

/** Turn a DRF error body into one readable message, shown to the user as-is. */
function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const b = body as Record<string, unknown>;
    const first = (v: unknown) => (Array.isArray(v) ? String(v[0]) : typeof v === 'string' ? v : null);
    const detail = first(b.detail) ?? first(b.non_field_errors) ?? first(b.message);
    if (detail) return detail;
    const [field, value] = Object.entries(b)[0] ?? [];
    const fieldMsg = first(value);
    if (field && fieldMsg) return `${field}: ${fieldMsg}`;
  }
  return `Request failed (${status}).`;
}

// One refresh at a time, shared by concurrent requests.
let refreshing: Promise<boolean> | null = null;

/** Swap the refresh token for a new pair (POST /accounts/refresh/). */
export function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    const refresh = getRefreshToken();
    if (!refresh || isExpired(refresh, 0)) return false;
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });
      if (!res.ok) return false;
      const data = (await res.json()) as { access?: string; refresh?: string };
      if (!data.access) return false;
      saveTokens(data.access, data.refresh ?? refresh); // refresh tokens rotate
      return true;
    } catch {
      return false;
    }
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<ApiResponse<T>> {
  if (!API_BASE_URL) {
    return { data: null, error: 'API base URL is not configured (VITE_API_BASE_URL).', loading: false };
  }
  const { skipAuth, ...init } = options;

  const send = async () => {
    const token = skipAuth ? null : getAccessToken();
    return fetch(`${API_BASE_URL}${endpoint}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  };

  try {
    if (!skipAuth && getRefreshToken() && isExpired(getAccessToken())) await refreshTokens();
    let response = await send();
    // Access token rejected (expired early / rotated) — refresh once and retry.
    if (response.status === 401 && !skipAuth && getRefreshToken() && (await refreshTokens())) {
      response = await send();
    }

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      return { data: null, error: errorMessage(body, response.status), errorBody: body, status: response.status, loading: false };
    }
    return { data: body as T, error: null, status: response.status, loading: false };
  } catch {
    return {
      data: null,
      error: 'Couldn’t reach MindCare’s servers. Check your connection and try again.',
      status: 0,
      loading: false,
    };
  }
}

// ——— Auth ———

/** POST /accounts/login/ → { access, refresh }. The access token carries a "role" claim. */
export function login(email: string, password: string) {
  return apiFetch<{ access: string; refresh: string }>('/accounts/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    skipAuth: true,
  });
}

/** POST /accounts/logout/ — blacklists the refresh token server-side. Best effort. */
export async function logoutRequest(): Promise<void> {
  const refresh = getRefreshToken();
  if (refresh) await apiFetch('/accounts/logout/', { method: 'POST', body: JSON.stringify({ refresh }) });
}

/**
 * POST /accounts/register/ — JSON body per the backend contract.
 * 201 on success (no tokens: sign in afterwards). Psychologist and NGO
 * accounts come back approval_status "pending" until an admin approves.
 */
export function register(payload: RegisterPayload) {
  return apiFetch<RegisteredUser>('/accounts/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}

/**
 * Flatten a DRF 400 body into { "email": msg, "profile.city": msg,
 * "profile.service_areas.1.city": msg, … } so forms can show each error
 * next to its field. Non-field errors land under "_".
 */
export function flattenFieldErrors(body: unknown, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  const walk = (value: unknown, path: string) => {
    if (typeof value === 'string') {
      out[path || '_'] ??= value;
    } else if (Array.isArray(value)) {
      if (value.every((v) => typeof v === 'string')) {
        if (value.length) out[path || '_'] ??= value.join(' ');
      } else {
        value.forEach((v, i) => walk(v, path ? `${path}.${i}` : String(i)));
      }
    } else if (value && typeof value === 'object') {
      for (const [k, v] of Object.entries(value)) {
        const key = k === 'non_field_errors' || k === 'detail' ? path : path ? `${path}.${k}` : k;
        walk(v, key);
      }
    }
  };
  walk(body, prefix);
  return out;
}

export async function getTherapists(): Promise<ApiResponse<{ id: string; name: string; specialty: string }[]>> {
  // TODO: return apiFetch('/therapists');
  return new Promise((resolve) =>
    setTimeout(() => {
      resolve({
        data: [
          { id: 't1', name: 'Dr. Tariq', specialty: 'Anxiety' },
          { id: 't2', name: 'Dr. Aisha', specialty: 'Depression' },
          { id: 't3', name: 'Dr. Sana', specialty: 'Trauma' },
        ],
        error: null,
        loading: false,
      });
    }, 600)
  );
}

// ——— Stories ———
// Until the backend exposes a stories endpoint, submissions are kept on this
// device so the author sees their story (marked "awaiting review") right away.

const MY_STORIES_KEY = 'mc_my_stories';
const STORY_COLORS = ['bg-emerald-700', 'bg-rose-400', 'bg-amber-600', 'bg-violet-500', 'bg-sky-600', 'bg-orange-500'];

export function getMyStories(): StoryEntry[] {
  try {
    const raw = localStorage.getItem(MY_STORIES_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as StoryEntry[]) : [];
  } catch {
    return [];
  }
}

export async function submitStory(payload: StorySubmission): Promise<ApiResponse<StoryEntry>> {
  // TODO: return apiFetch('/stories', { method: 'POST', body: JSON.stringify(payload) });
  const name = payload.name.trim() || 'Anonymous';
  const story: StoryEntry = {
    id: `my-story-${Date.now()}`,
    quote: payload.quote.trim(),
    name,
    age: payload.age,
    location: payload.location.trim(),
    tag: payload.tag,
    avatarInitials: `${name.charAt(0).toUpperCase()}${payload.age ? Math.floor(payload.age / 10) : ''}`,
    avatarColor: STORY_COLORS[Math.floor(Math.random() * STORY_COLORS.length)],
    pending: true,
  };

  return new Promise((resolve) =>
    setTimeout(() => {
      try {
        localStorage.setItem(MY_STORIES_KEY, JSON.stringify([story, ...getMyStories()]));
      } catch {
        // Storage unavailable (private mode) — the story still shows for this visit.
      }
      resolve({ data: story, error: null, loading: false });
    }, 700)
  );
}

// ——— Public platform stats ———
// Backend contract: GET /stats/public/ → { people_in_care, verified_therapists, cities }
// (aggregate counts only, no auth). Until that endpoint is live, or if it
// fails, every count shows 0 rather than a made-up figure.

export const EMPTY_PLATFORM_STATS: PlatformStats = { people_in_care: 0, verified_therapists: 0, cities: 0 };

const toCount = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) && v > 0 ? Math.floor(v) : 0);

export async function getPlatformStats(): Promise<PlatformStats> {
  const res = await apiFetch<Partial<PlatformStats>>('/stats/public/');
  if (!res.data) return EMPTY_PLATFORM_STATS;
  return {
    people_in_care: toCount(res.data.people_in_care),
    verified_therapists: toCount(res.data.verified_therapists),
    cities: toCount(res.data.cities),
  };
}

// ——— App download link (Get started page) ———

export async function requestAppLink(email: string): Promise<ApiResponse<{ sent: true }>> {
  // TODO: needs a backend endpoint that emails the download link; until then nothing is sent.
  void email;
  return new Promise((resolve) =>
    setTimeout(() => resolve({ data: { sent: true }, error: null, loading: false }), 600)
  );
}

// ——— Contact ———

export async function sendContactMessage(
  payload: ContactMessage
): Promise<ApiResponse<{ received: true }>> {
  // TODO: return apiFetch('/contact', { method: 'POST', body: JSON.stringify(payload) });
  console.info('[MindCare] sendContactMessage called with', { ...payload, message: '[redacted]' });

  return new Promise((resolve) =>
    setTimeout(() => resolve({ data: { received: true }, error: null, loading: false }), 700)
  );
}

export { apiFetch };
