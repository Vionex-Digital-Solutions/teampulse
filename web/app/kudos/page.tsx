"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

// Safely pull an HTTP status off an unknown thrown value. Our api client throws
// an ApiError ({ status, message }); anything else (a network TypeError, etc.)
// has no status and maps to the generic "can't connect" message via friendlyError.
function errorStatus(err: unknown): number | undefined {
  if (typeof err === "object" && err !== null && "status" in err) {
    const status = (err as { status: unknown }).status;
    return typeof status === "number" ? status : undefined;
  }
  return undefined;
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

// Narrow an untrusted SSE payload to a KudosResponse before we trust it.
// JSON.parse only proves it's valid JSON — a valid-JSON-but-wrong-shape event
// (null, a number, a partial object, a stray keep-alive) must never reach the
// feed: at minimum it would prepend a card with an `undefined` React key and a
// broken dedup. We check exactly the fields the feed reads.
function isKudosResponse(value: unknown): value is KudosResponse {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "string" &&
    typeof v.sender_id === "string" &&
    typeof v.receiver_id === "string" &&
    typeof v.category === "string" &&
    typeof v.message === "string" &&
    typeof v.created_at === "string" &&
    (v.message_ar === null ||
      v.message_ar === undefined ||
      typeof v.message_ar === "string")
  );
}

export default function KudosPage() {
  // ---- Feed state ----
  const [feed, setFeed] = useState<KudosResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [feedError, setFeedError] = useState<string>("");
  // Non-blocking notices that must NOT replace the feed: a background refresh
  // (e.g. after posting a kudos) or a "load more" that fails. The existing feed
  // stays on screen; we surface these inline so the failure is recoverable
  // without wiping content the user is already reading.
  const [refreshError, setRefreshError] = useState<string>("");
  const [loadMoreError, setLoadMoreError] = useState<string>("");
  // Pagination: whether a "load more" fetch is in flight, and whether the last
  // page came back full (so there may still be more to load).
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  // Message for a visually-hidden live region: screen-reader users can't see a
  // new kudos slide into the feed, so we announce live (SSE) arrivals here.
  const [liveAnnouncement, setLiveAnnouncement] = useState("");

  // Cancellation + lifecycle guards for feed fetches. `feedControllerRef` holds
  // the in-flight fetch so a newer request (retry, post-submit refresh, next
  // "load more") can abort the previous one — latest request wins, and a slow
  // stale response can never clobber newer state. `mountedRef` gates every
  // setState so an in-flight fetch that resolves after unmount is a no-op.
  const feedControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

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
  const loadFeed = useCallback(
    async (offset: number, opts: { silent?: boolean } = {}) => {
      const replacing = offset === 0;
      // A "silent" replace is a background refresh (e.g. right after posting a
      // kudos): it must not flip the whole feed to the blocking loading/error
      // UI, so on failure it keeps the existing feed and shows a soft notice.
      const silent = opts.silent ?? false;

      // Supersede any in-flight feed fetch: the newest request wins and the old
      // one is cancelled so its response can't land on top of newer state.
      feedControllerRef.current?.abort();
      const controller = new AbortController();
      feedControllerRef.current = controller;

      // Clear the recoverable notices on every new attempt.
      setRefreshError("");
      setLoadMoreError("");
      if (replacing) {
        // A page-1 load owns the primary loading UI and cancels any pending
        // "load more" (we just aborted its fetch above).
        setIsLoadingMore(false);
        if (!silent) {
          setIsLoading(true);
          setFeedError("");
        }
      } else {
        setIsLoadingMore(true);
      }

      try {
        const data = await api.getKudosFeed(
          { limit: PAGE_SIZE, offset },
          { signal: controller.signal }
        );
        // Bail if we unmounted or were superseded while the fetch was in flight.
        if (!mountedRef.current || controller.signal.aborted) return;
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
      } catch (err) {
        // A cancelled/superseded fetch or a post-unmount resolution is not a
        // real error — never surface it. Any abort we trigger (supersede or
        // unmount) is on this controller, so `signal.aborted` covers the
        // AbortError case too; no need to sniff the thrown value's name.
        if (!mountedRef.current || controller.signal.aborted) {
          return;
        }
        const status = errorStatus(err);
        if (replacing && !silent) {
          // Initial load / explicit retry failed with nothing to preserve:
          // show the full error screen.
          setFeedError(friendlyError(status));
        } else if (replacing) {
          // Background refresh failed: keep the existing feed, note it softly.
          setRefreshError(friendlyError(status));
        } else {
          // "Load more" failed: keep what we have; the button stays available
          // to retry (hasMore is untouched on error).
          setLoadMoreError(friendlyError(status));
        }
      } finally {
        // Only the newest fetch settles the loading flags, and only while
        // mounted — a superseded fetch must not toggle UI the new one now owns.
        if (mountedRef.current && feedControllerRef.current === controller) {
          if (replacing && !silent) setIsLoading(false);
          else if (!replacing) setIsLoadingMore(false);
        }
      }
    },
    []
  );

  // Fetch the next page, starting after everything we already show.
  const loadMore = useCallback(() => {
    loadFeed(feed.length);
  }, [loadFeed, feed.length]);

  useEffect(() => {
    // Re-arm on (re)mount — React StrictMode mounts, unmounts, then remounts.
    mountedRef.current = true;
    loadFeed(0);
    return () => {
      // Block any late setState and cancel the in-flight fetch on unmount.
      mountedRef.current = false;
      feedControllerRef.current?.abort();
    };
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

    // Distinguishes the first successful connect from later auto-reconnects.
    // Local to this effect run (not a ref) so a StrictMode remount starts fresh
    // and doesn't mistake its initial connect for a reconnect.
    let established = false;

    es.onopen = () => {
      // The first open is the initial connection; history is already loaded by
      // loadFeed(0) on mount, so there's nothing to reconcile. Every later open
      // is a browser auto-reconnect after a dropped connection — and any kudos
      // created during that gap were never delivered to us. The backend sends
      // no event id, so the browser cannot replay them via Last-Event-ID (see
      // note below); the honest frontend-only recovery is to silently refetch
      // page 1 and let dedup-by-id merge it in. This backfills events that still
      // fall within the first page; a longer outage needs backend replay.
      if (!established) {
        established = true;
        return;
      }
      loadFeed(0, { silent: true });
    };

    es.onmessage = (event) => {
      // Each event's data is one KudosResponse JSON object (same shape as feed
      // items). Parse defensively, then validate the shape: a bad or unexpected
      // payload must be dropped, never prepended.
      let incoming: unknown;
      try {
        incoming = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!isKudosResponse(incoming)) return;
      const kudos = incoming;
      // Announce the arrival for screen readers. Every stream message is a real
      // new-kudos event on the backend, so announcing here is accurate even
      // though the visual prepend below dedupes a kudos you sent yourself.
      setLiveAnnouncement(`New ${categoryLabel(kudos.category)} kudos received.`);
      // Prepend newest-first, but ignore anything already shown — e.g. a kudos
      // you just sent arrives via both loadFeed(0) and this stream.
      setFeed((prev) =>
        prev.some((k) => k.id === kudos.id) ? prev : [kudos, ...prev]
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
    // loadFeed is stable (useCallback with []), so this effect still connects
    // exactly once; it's in deps only because onopen calls it.
  }, [loadFeed]);

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
      // Refresh the feed from page 1 so the new kudos appears at the top. Use a
      // silent refresh: the submit already succeeded, so if this background
      // fetch fails we must keep the existing feed on screen (and the SSE stream
      // will surface the new kudos anyway) instead of wiping it with an error.
      await loadFeed(0, { silent: true });
    } catch (err) {
      // Map HTTP status codes to friendly messages instead of exposing raw
      // status codes or backend error strings to the user.
      setSubmitError(friendlyError(errorStatus(err)));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-navy">Kudos</h1>

      {/* Visually-hidden live region for live (SSE) arrivals. Kept mounted so
          the announcement is picked up when its text changes; polite so it
          never interrupts what the user is doing. */}
      <p className="sr-only" aria-live="polite">
        {liveAnnouncement}
      </p>

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

        {/* Submit outcome in a polite live region so it's announced when it
            appears — otherwise a screen reader gives no feedback that the send
            succeeded or failed. */}
        <div aria-live="polite">
          {success && (
            <p className="text-sm text-green-600">✅ Kudos sent!</p>
          )}
          {submitError && (
            <p className="text-sm text-red-600">❌ {submitError}</p>
          )}
        </div>
      </section>

      {/* ---- Kudos feed ---- */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-navy">Recent kudos</h2>

        {/* Non-blocking notice for a failed background refresh (e.g. after
            posting). The existing feed below stays visible; this only informs
            and offers a soft retry. */}
        {refreshError && !feedError && (
          <p className="text-sm text-amber-600" role="status">
            ⚠ Couldn&apos;t refresh the feed. {refreshError}{" "}
            <button
              type="button"
              onClick={() => loadFeed(0, { silent: true })}
              className="text-accent underline"
            >
              Try again
            </button>
          </p>
        )}

        {/* Loading / error / empty status share one polite live region so a
            screen reader announces the transitions between them. The list of
            kudos is rendered outside this region: announcing every card
            wholesale (including raw UUIDs) would be noise, not help. */}
        <div role="status" aria-live="polite">
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
          ) : null}
        </div>

        {!isLoading && !feedError && feed.length > 0 && (
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

        {/* A failed "Load more" keeps the existing feed on screen and reports
            the failure inline; the button below stays available to retry. */}
        {loadMoreError && (
          <p className="text-sm text-amber-600" role="status">
            ⚠ {loadMoreError}
          </p>
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
            {isLoadingMore
              ? "Loading…"
              : loadMoreError
                ? "Try again"
                : "Load more"}
          </button>
        )}
      </section>
    </div>
  );
}
