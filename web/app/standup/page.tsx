"use client";

import { useState } from "react";
import { api } from "@/lib/api";

// Mirror the backend's max_length constraint (see backend/app/schemas/standup.py)
// so the client rejects over-long input before it ever hits the server. The
// backend remains the source of truth; this is purely a UX convenience.
const MAX_LENGTH = 2000;

type FieldErrors = {
  yesterday?: string;
  today?: string;
  blockers?: string;
};

// Translate an HTTP status code into a friendly, user-facing message.
// We deliberately never surface the raw status code or backend error text.
function friendlyError(status?: number): string {
  if (!status) {
    return "Unable to connect to the server. Please try again later.";
  }
  if (status === 400 || status === 422) {
    return "Please check your input and try again.";
  }
  if (status === 500) {
    return "We couldn't submit your standup. Please try again later.";
  }
  return "Something unexpected happened. Please try again.";
}

// Pure validation: derive the set of field errors from the current values.
// Keeping this out of the component makes the rules easy to read and test.
function validate(values: {
  yesterday: string;
  today: string;
  blockers: string;
}): FieldErrors {
  const errors: FieldErrors = {};

  if (!values.yesterday.trim()) {
    errors.yesterday = "Yesterday is required.";
  } else if (values.yesterday.length > MAX_LENGTH) {
    errors.yesterday = `Please keep this under ${MAX_LENGTH} characters.`;
  }

  if (!values.today.trim()) {
    errors.today = "Today is required.";
  } else if (values.today.length > MAX_LENGTH) {
    errors.today = `Please keep this under ${MAX_LENGTH} characters.`;
  }

  // Blockers is optional, but still bounded when provided.
  if (values.blockers.length > MAX_LENGTH) {
    errors.blockers = `Please keep this under ${MAX_LENGTH} characters.`;
  }

  return errors;
}

export default function StandupPage() {
  const [yesterday, setYesterday] = useState("");
  const [today, setToday] = useState("");
  const [blockers, setBlockers] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<boolean>(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Guard against double submission (e.g. rapid double-clicks or Enter).
    if (isSubmitting) return;

    const errors = validate({ yesterday, today, blockers });
    setFieldErrors(errors);
    // Prevent submit when any field fails validation.
    if (Object.keys(errors).length > 0) {
      setError("");
      setSuccess(false);
      return;
    }

    setIsSubmitting(true);
    setError("");
    setSuccess(false);
    try {
      await api.submitStandup({
        yesterday,
        today,
        blockers: blockers || undefined,
      });
      setSuccess(true);
    } catch (err: any) {
      // Map HTTP status codes to friendly messages instead of exposing
      // raw status codes or backend error strings to the user.
      setError(friendlyError(err?.status));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy">Async Standup</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="yesterday" className="block font-medium mb-1">
            Yesterday
          </label>
          <textarea
            id="yesterday"
            value={yesterday}
            onChange={(e) => {
              setYesterday(e.target.value);
              // Clear this field's error as soon as the user edits it.
              if (fieldErrors.yesterday) {
                setFieldErrors((prev) => ({ ...prev, yesterday: undefined }));
              }
            }}
            disabled={isSubmitting}
            aria-invalid={!!fieldErrors.yesterday}
            aria-describedby={
              fieldErrors.yesterday ? "yesterday-error" : undefined
            }
            className="w-full rounded-lg border p-2 disabled:opacity-60"
            rows={3}
          />
          {fieldErrors.yesterday && (
            <p id="yesterday-error" className="mt-1 text-sm text-red-600">
              {fieldErrors.yesterday}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="today" className="block font-medium mb-1">
            Today
          </label>
          <textarea
            id="today"
            value={today}
            onChange={(e) => {
              setToday(e.target.value);
              if (fieldErrors.today) {
                setFieldErrors((prev) => ({ ...prev, today: undefined }));
              }
            }}
            disabled={isSubmitting}
            aria-invalid={!!fieldErrors.today}
            aria-describedby={fieldErrors.today ? "today-error" : undefined}
            className="w-full rounded-lg border p-2 disabled:opacity-60"
            rows={3}
          />
          {fieldErrors.today && (
            <p id="today-error" className="mt-1 text-sm text-red-600">
              {fieldErrors.today}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="blockers" className="block font-medium mb-1">
            Blockers (optional)
          </label>
          <textarea
            id="blockers"
            value={blockers}
            onChange={(e) => {
              setBlockers(e.target.value);
              if (fieldErrors.blockers) {
                setFieldErrors((prev) => ({ ...prev, blockers: undefined }));
              }
            }}
            disabled={isSubmitting}
            aria-invalid={!!fieldErrors.blockers}
            aria-describedby={
              fieldErrors.blockers ? "blockers-error" : undefined
            }
            className="w-full rounded-lg border p-2 disabled:opacity-60"
            rows={3}
          />
          {fieldErrors.blockers && (
            <p id="blockers-error" className="mt-1 text-sm text-red-600">
              {fieldErrors.blockers}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="bg-accent text-white px-5 py-2 rounded-lg font-medium disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Submitting..." : "Submit"}
        </button>
      </form>

      {success && (
        <p className="text-sm text-green-600">
          ✅ Standup submitted successfully!
        </p>
      )}
      {error && <p className="text-sm text-red-600">❌ {error}</p>}
    </div>
  );
}
