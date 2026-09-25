// ============================================================
// MindCare — API Service Layer
// All HTTP calls live here. Swap dummy data for real endpoints.
// ============================================================

import { API_BASE_URL } from '../constants';
import type { SignInPayload, SignUpPayload, ApiResponse, StoryEntry, StorySubmission, ContactMessage } from '../types';

// ——— Generic fetch wrapper (CSRF + auth headers ready) ———
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('mc_access_token') : null;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include', // send cookies for CSRF protection
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ message: 'Unknown error' }));
      return { data: null, error: err.message ?? 'Request failed', loading: false };
    }

    const data: T = await response.json();
    return { data, error: null, loading: false };
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Network error';
    return { data: null, error: message, loading: false };
  }
}

// ——— Auth endpoints (placeholder — wire up when backend ready) ———

export async function signIn(
  payload: SignInPayload
): Promise<ApiResponse<{ token: string; user: { id: string; name: string; role: string } }>> {
  // TODO: replace with real call → return apiFetch('/auth/sign-in', { method: 'POST', body: JSON.stringify(payload) });
  console.info('[MindCare] signIn called with', payload);

  // Dummy response for UI testing
  return new Promise((resolve) =>
    setTimeout(() => {
      resolve({
        data: { token: 'dummy-jwt-token', user: { id: '1', name: 'Layla Ahmed', role: 'client' } },
        error: null,
        loading: false,
      });
    }, 800)
  );
}

export async function signUp(
  payload: SignUpPayload
): Promise<ApiResponse<{ token: string; userId: string }>> {
  // TODO: return apiFetch('/auth/sign-up', { method: 'POST', body: JSON.stringify(payload) });
  console.info('[MindCare] signUp called with', payload);

  return new Promise((resolve) =>
    setTimeout(() => {
      resolve({ data: { token: 'dummy-jwt-token', userId: 'new-user-123' }, error: null, loading: false });
    }, 800)
  );
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
