"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type KudosCategory,
  type KudosResponse,
} from "@/lib/api";

// Mirror the backend's max_length constraint (see backend/app/schemas/kudos.py)
// so the client rejects over-long input before it ever hits the server. The
// backend remains the source of truth; this is purely a UX convenience.
const MAX_MESSAGE_LENGTH = 1000;

// How many kudos to fetch per page. When a page comes back full, there may be
// more to load; a short page means we've reached the end. (Backend caps the
// limit at 100 — see backend/app/api/v1/kudos.py.)
const PAGE_SIZE = 20;

// Backend origin for the live SSE stream. The stream lives on the FastAPI
// origin (not Next's), so it needs an absolute URL. Mirrors web/lib/api.ts,
// which keeps its BASE_URL private; if that's ever exported, import it instead.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// The fixed set of categories the backend accepts (KudosCategory enum), paired
// with human-friendly labels for the <select>. Keep the values in sync with
// backend/app/schemas/kudos.py.
const CATEGORIES: { value: KudosCategory; label: string }[] = [
  { value: "teamwork", label: "Teamwork" },
  { value: "innovation", label: "Innovation" },
  { value: "mentorship", label: "Mentorship" },
  { value: "above_and_beyond", label: "Above and Beyond" },
  { value: "quality", label: "Quality" },
  { value: "communication", label: "Communication" },
];

type FieldErrors = {
  receiver_id?: string;
  message?: string;
  message_ar?: string;
};

// Translate an HTTP status code into a friendly, user-facing message. We
// deliberately never surface the raw status code or backend error text.
// Same approach as the Standup page for consistency.
function friendlyError(status?: number): string {
  if (!status) {
    return "Unable to connect to the server. Please try again later.";
  }
  if (status === 400) {
    return "You can't send kudos to yourself.";
  }
  if (status === 401) {
    return "You need to be signed in to send or view kudos.";
  }
  if (status === 404) {
    return "That teammate could not be found.";
  }
  if (status === 422) {
    return "Please check your input and try again.";
  }
  if (status === 500) {
    return "We couldn't complete that just now. Please try again later.";
  }
  return "Something unexpected happened. Please try again.";
}

// Pure validation: derive the set of field errors from the current values.
// Keeping this out of the component makes the rules easy to read and test.
function validate(values: {
  receiver_id: string;
  message: string;
  message_ar: string;
}): FieldErrors {
  const errors: FieldErrors = {};

  if (!values.receiver_id.trim()) {
    errors.receiver_id = "Recipient is required.";
  }

  if (!values.message.trim()) {
    errors.message = "Message is required.";
  } else if (values.message.length > MAX_MESSAGE_LENGTH) {
    errors.message = `Please keep this under ${MAX_MESSAGE_LENGTH} characters.`;
  }

  // Arabic message is optional, but still bounded when provided.
  if (values.message_ar.length > MAX_MESSAGE_LENGTH) {
    errors.message_ar = `Please keep this under ${MAX_MESSAGE_LENGTH} characters.`;
  }

  return errors;
}

// Turn a stored category value (e.g. "above_and_beyond") into a readable label,
// falling back to the raw value for anything we don't recognise.
function categoryLabel(value: string): string {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

// Format the ISO 8601 created_at into something human-readable. Guard against
// an unparseable value so a bad timestamp never breaks the whole feed.
function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

export default function KudosPage() {
  // ---- Feed state ----
  const [feed, setFeed] = useState<KudosResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [feedError, setFeedError] = useState<string>("");
  // Pagination: whether a "load more" fetch is in flight, and whether the last
  // page came back full (so there may still be more to load).
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);

  // ---- Form state ----
  const [receiverId, setReceiverId] = useState("");
  const [category, setCategory] = useState<KudosCategory>("teamwork");
  const [message, setMessage] = useState("");
  const [messageAr, setMessageAr] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string>("");
  const [success, setSuccess] = useState(false);

  // Load the kudos feed. Wrapped in useCallback so we can call it on mount and
  // again after a successful submission without redefining it each render.
  // offset === 0 loads the first page and replaces the list (fresh load, retry,
  // or after submitting); offset > 0 appends the next page ("Load more").
  const loadFeed = useCallback(async (offset: number) => {
    const replacing = offset === 0;
    // First page drives the full-feed loading/error UI; "load more" uses its
    // own flag so the existing feed stays visible while the next page loads.
    if (replacing) {
      setIsLoading(true);
      setFeedError("");
    } else {
      setIsLoadingMore(true);
    }
    try {
      const data = await api.getKudosFeed({ limit: PAGE_SIZE, offset });
      // On append, drop any items already shown. A live SSE event arriving
      // while this "load more" is in flight shifts the backend's offset window,
      // so the next page can overlap what we already have; dedup by id keeps
      // each kudos (and its React key) unique. Replacing needs no dedup.
      setFeed((prev) => {
        if (replacing) return data;
        const seen = new Set(prev.map((k) => k.id));
        return [...prev, ...data.filter((k) => !seen.has(k.id))];
      });
      // A full page means there may be more; a short page is the end.
      setHasMore(data.length === PAGE_SIZE);
    } catch (err: any) {
      setFeedError(friendlyError(err?.status));
    } finally {
      if (replacing) setIsLoading(false);
      else setIsLoadingMore(false);
    }
  }, []);

  // Fetch the next page, starting after everything we already show.
  const loadMore = useCallback(() => {
    loadFeed(feed.length);
  }, [loadFeed, feed.length]);

  useEffect(() => {
    loadFeed(0);
  }, [loadFeed]);

  // ---- Live updates (Server-Sent Events) ----
  // Subscribe to GET /api/v1/kudos/stream, which pushes each newly created
  // kudos as it happens. This sits on top of the initial fetch: loadFeed(0)
  // still loads history; SSE only adds arrivals that happen after we connect.
  useEffect(() => {
    // EventSource can't send an Authorization header, so the backend takes the
    // JWT as a ?token= query param. There's no token store in the app yet, so
    // we look in localStorage and skip the live feed entirely when it's absent
    // — a tokenless connection would 401, which EventSource treats as a fatal
    // error (it does not retry non-2xx responses); onerror below handles that.
    const token =
      typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) return;

    const es = new EventSource(
      `${API_BASE_URL}/api/v1/kudos/stream?token=${encodeURIComponent(token)}`
    );

    es.onmessage = (event) => {
      // Each event's data is one KudosResponse JSON object (same shape as feed
      // items). Guard against a malformed payload so a bad event can't crash us.
      let incoming: KudosResponse;
      try {
        incoming = JSON.parse(event.data);
      } catch {
        return;
      }
      // Prepend newest-first, but ignore anything already shown — e.g. a kudos
      // you just sent arrives via both loadFeed(0) and this stream.
      setFeed((prev) =>
        prev.some((k) => k.id === incoming.id) ? prev : [incoming, ...prev]
      );
    };

    es.onerror = () => {
      // Two cases land here. (1) A transient drop of an open stream: readyState
      // is CONNECTING and EventSource is already reconnecting on its own — leave
      // it alone. (2) A fatal failure (e.g. a 401 from an expired/invalid token):
      // readyState is CLOSED and it will never retry, so close explicitly to
      // stop leaking a dead handle. In neither case do we touch feedError: the
      // history loaded via loadFeed(0) is still valid, and hijacking the feed's
      // error UI over a lost *live* connection would misrepresent that state.
      if (es.readyState === EventSource.CLOSED) es.close();
    };

    // Close the stream on unmount so we don't leak it or keep reconnecting.
    return () => es.close();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Guard against double submission (e.g. rapid double-clicks or Enter).
    if (isSubmitting) return;

    const errors = validate({
      receiver_id: receiverId,
      message,
      message_ar: messageAr,
    });
    setFieldErrors(errors);
    // Prevent submit when any field fails validation.
    if (Object.keys(errors).length > 0) {
      setSubmitError("");
      setSuccess(false);
      return;
    }

    setIsSubmitting(true);
    setSubmitError("");
    setSuccess(false);
    try {
      await api.submitKudos({
        receiver_id: receiverId.trim(),
        category,
        message: message.trim(),
        message_ar: messageAr.trim() || undefined,
      });
      setSuccess(true);
      // Reset the message fields; keep category so sending several in a row is
      // less tedious. Clear the recipient to avoid accidental repeats.
      setReceiverId("");
      setMessage("");
      setMessageAr("");
      // Refresh the feed from page 1 so the new kudos appears at the top.
      await loadFeed(0);
    } catch (err: any) {
      // Map HTTP status codes to friendly messages instead of exposing raw
      // status codes or backend error strings to the user.
      setSubmitError(friendlyError(err?.status));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-navy">Kudos</h1>

      {/* ---- Send kudos form ---- */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-navy">Send kudos</h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="receiver_id" className="block font-medium mb-1">
              Recipient (user ID)
            </label>
            <input
              id="receiver_id"
              type="text"
              value={receiverId}
              onChange={(e) => {
                setReceiverId(e.target.value);
                if (fieldErrors.receiver_id) {
                  setFieldErrors((prev) => ({
                    ...prev,
                    receiver_id: undefined,
                  }));
                }
              }}
              disabled={isSubmitting}
              placeholder="3fa85f64-5717-4562-b3fc-2c963f66afa6"
              aria-invalid={!!fieldErrors.receiver_id}
              aria-describedby={
                fieldErrors.receiver_id ? "receiver_id-error" : undefined
              }
              className="w-full rounded-lg border p-2 disabled:opacity-60"
            />
            {fieldErrors.receiver_id && (
              <p id="receiver_id-error" className="mt-1 text-sm text-red-600">
                {fieldErrors.receiver_id}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="category" className="block font-medium mb-1">
              Category
            </label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value as KudosCategory)}
              disabled={isSubmitting}
              className="w-full rounded-lg border p-2 disabled:opacity-60"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="message" className="block font-medium mb-1">
              Message
            </label>
            <textarea
              id="message"
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                if (fieldErrors.message) {
                  setFieldErrors((prev) => ({ ...prev, message: undefined }));
                }
              }}
              disabled={isSubmitting}
              aria-invalid={!!fieldErrors.message}
              aria-describedby={fieldErrors.message ? "message-error" : undefined}
              className="w-full rounded-lg border p-2 disabled:opacity-60"
              rows={3}
            />
            {fieldErrors.message && (
              <p id="message-error" className="mt-1 text-sm text-red-600">
                {fieldErrors.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="message_ar" className="block font-medium mb-1">
              Message in Arabic (optional)
            </label>
            <textarea
              id="message_ar"
              value={messageAr}
              onChange={(e) => {
                setMessageAr(e.target.value);
                if (fieldErrors.message_ar) {
                  setFieldErrors((prev) => ({
                    ...prev,
                    message_ar: undefined,
                  }));
                }
              }}
              disabled={isSubmitting}
              dir="rtl"
              aria-invalid={!!fieldErrors.message_ar}
              aria-describedby={
                fieldErrors.message_ar ? "message_ar-error" : undefined
              }
              className="w-full rounded-lg border p-2 disabled:opacity-60"
              rows={3}
            />
            {fieldErrors.message_ar && (
              <p id="message_ar-error" className="mt-1 text-sm text-red-600">
                {fieldErrors.message_ar}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-accent text-white px-5 py-2 rounded-lg font-medium disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Sending..." : "Send kudos"}
          </button>
        </form>

        {success && (
          <p className="text-sm text-green-600">✅ Kudos sent!</p>
        )}
        {submitError && (
          <p className="text-sm text-red-600">❌ {submitError}</p>
        )}
      </section>

      {/* ---- Kudos feed ---- */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-navy">Recent kudos</h2>

        {isLoading ? (
          <p className="text-sm text-slate-600">Loading feed…</p>
        ) : feedError ? (
          <div className="space-y-2">
            <p className="text-sm text-red-600">❌ {feedError}</p>
            <button
              type="button"
              onClick={() => loadFeed(0)}
              className="text-sm text-accent underline"
            >
              Try again
            </button>
          </div>
        ) : feed.length === 0 ? (
          <p className="text-sm text-slate-600">
            No kudos yet. Be the first to recognise a teammate!
          </p>
        ) : (
          <ul className="space-y-3">
            {feed.map((kudos) => (
              <li
                key={kudos.id}
                className="rounded-lg border p-4 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-block rounded-full bg-navy text-white text-xs px-2 py-1">
                    {categoryLabel(kudos.category)}
                  </span>
                  <span className="text-xs text-slate-400">
                    {formatDate(kudos.created_at)}
                  </span>
                </div>
                <p className="whitespace-pre-wrap">{kudos.message}</p>
                {kudos.message_ar && (
                  <p className="whitespace-pre-wrap text-slate-600" dir="rtl">
                    {kudos.message_ar}
                  </p>
                )}
                <p className="text-xs text-slate-400">
                  From {kudos.sender_id} → {kudos.receiver_id}
                </p>
              </li>
            ))}
          </ul>
        )}

        {/* Only offer "Load more" once the first page is shown and the last
            page came back full. Disabled while the next page is loading. */}
        {!isLoading && !feedError && hasMore && (
          <button
            type="button"
            onClick={loadMore}
            disabled={isLoadingMore}
            className="text-sm text-accent underline disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoadingMore ? "Loading…" : "Load more"}
          </button>
        )}
      </section>
    </div>
  );
}
