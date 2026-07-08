// Tiny API client for the TeamPulse FastAPI backend.
// Base URL comes from NEXT_PUBLIC_API_URL (see .env.example).

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ApiError = { status: number; message: string };

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      /* ignore */
    }
    throw { status: res.status, message } as ApiError;
  }

  // Some endpoints (204) return no body
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---- Pulse ----
export type PulseCreate = {
  mood: number;
  energy: number;
  has_blocker: boolean;
  note?: string;
  note_ar?: string;
};

// ---- Standup ----
export type StandupCreate = {
  yesterday: string;
  today: string;
  blockers?: string;
};

// ---- Kudos ----
// Mirrors the backend KudosCategory enum (see backend/app/schemas/kudos.py).
export type KudosCategory =
  | "teamwork"
  | "innovation"
  | "mentorship"
  | "above_and_beyond"
  | "quality"
  | "communication";

// Request body for POST /api/v1/kudos. There is no sender_id: the sender is
// always the authenticated user (taken from the JWT on the backend).
export type KudosCreate = {
  receiver_id: string;
  category: KudosCategory;
  message: string;
  message_ar?: string;
};

// A single kudos entry as returned by POST /kudos and GET /kudos/feed.
export type KudosResponse = {
  id: string;
  sender_id: string;
  receiver_id: string;
  category: string;
  message: string;
  message_ar: string | null;
  created_at: string;
};

export const api = {
  health: () => request<{ status: string }>("/health"),

  submitPulse: (data: PulseCreate) =>
    request("/api/v1/pulse", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  submitStandup: (data: StandupCreate) =>
    request("/api/v1/standup", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMyPulses: () => request("/api/v1/pulse/me"),

  getTeamPulses: () => request("/api/v1/pulse/team"),

  // limit/offset are optional; when omitted the backend defaults apply
  // (limit=50, offset=0), so existing callers keep working unchanged. An
  // optional AbortSignal lets the caller cancel an in-flight fetch (used by the
  // kudos page to drop superseded/unmounted requests); it flows straight
  // through to fetch via request()'s options, so `request()` itself is unchanged.
  getKudosFeed: (
    params: { limit?: number; offset?: number } = {},
    options: { signal?: AbortSignal } = {}
  ) => {
    const qs = new URLSearchParams();
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<KudosResponse[]>(`/api/v1/kudos/feed${suffix}`, {
      signal: options.signal,
    });
  },

  submitKudos: (data: KudosCreate) =>
    request<KudosResponse>("/api/v1/kudos", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getTeamStandups: () => request("/api/v1/standup/team"),
};
