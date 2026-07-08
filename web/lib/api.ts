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

export const api = {
  health: () => request<{ status: string }>("/health"),

  submitPulse: (data: PulseCreate) =>
    request("/api/v1/pulses", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  submitStandup: (data: StandupCreate) =>
    request("/api/v1/standups", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getMyPulses: () => request("/api/v1/pulses/me"),

  getTeamPulses: () => request("/api/v1/pulses/summary?scope=team"),

  getKudosFeed: () => request("/api/v1/kudos/feed"),

  getTeamStandups: () => request("/api/v1/standups?scope=team"),
};
