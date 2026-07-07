"use client";

import { useState } from "react";
import { api } from "@/lib/api";

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

export default function StandupPage() {
  const [yesterday, setYesterday] = useState("");
  const [today, setToday] = useState("");
  const [blockers, setBlockers] = useState("");
  const [status, setStatus] = useState<string>("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!yesterday.trim() || !today.trim()) {
      setStatus("Please fill in Yesterday and Today.");
      return;
    }
    setStatus("Submitting...");
    try {
      await api.submitStandup({
        yesterday,
        today,
        blockers: blockers || undefined,
      });
      setStatus("✅ Standup submitted successfully!");
    } catch (err: any) {
      // Map HTTP status codes to friendly messages instead of exposing
      // raw status codes or backend error strings to the user.
      setStatus(`❌ ${friendlyError(err?.status)}`);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy">Async Standup</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block font-medium mb-1">Yesterday</label>
          <textarea
            value={yesterday}
            onChange={(e) => setYesterday(e.target.value)}
            className="w-full rounded-lg border p-2"
            rows={3}
          />
        </div>

        <div>
          <label className="block font-medium mb-1">Today</label>
          <textarea
            value={today}
            onChange={(e) => setToday(e.target.value)}
            className="w-full rounded-lg border p-2"
            rows={3}
          />
        </div>

        <div>
          <label className="block font-medium mb-1">Blockers (optional)</label>
          <textarea
            value={blockers}
            onChange={(e) => setBlockers(e.target.value)}
            className="w-full rounded-lg border p-2"
            rows={3}
          />
        </div>

        <button
          type="submit"
          className="bg-accent text-white px-5 py-2 rounded-lg font-medium"
        >
          Submit
        </button>
      </form>

      {status && <p className="text-sm">{status}</p>}
    </div>
  );
}
