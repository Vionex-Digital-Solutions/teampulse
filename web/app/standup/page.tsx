"use client";

import { useState } from "react";
import { api } from "@/lib/api";

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
      setStatus("✅ Standup submitted!");
    } catch (err: any) {
      // The backend endpoint is still a stub (NotImplementedError) —
      // it will 500 until the backend team implements it.
      setStatus(`❌ ${err.status}: ${err.message}`);
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
