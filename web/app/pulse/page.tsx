"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function PulsePage() {
  const [mood, setMood] = useState(3);
  const [energy, setEnergy] = useState(3);
  const [hasBlocker, setHasBlocker] = useState(false);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<string>("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Submitting...");
    try {
      await api.submitPulse({
        mood,
        energy,
        has_blocker: hasBlocker,
        note: note || undefined,
      });
      setStatus("✅ Pulse submitted!");
    } catch (err: any) {
      // The backend endpoint is still a stub (NotImplementedError) —
      // it will 500 until the backend team implements it.
      setStatus(`❌ ${err.status}: ${err.message}`);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy">Daily Pulse Check-in</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block font-medium mb-1">Mood: {mood}/5</label>
          <input
            type="range"
            min={1}
            max={5}
            value={mood}
            onChange={(e) => setMood(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block font-medium mb-1">Energy: {energy}/5</label>
          <input
            type="range"
            min={1}
            max={5}
            value={energy}
            onChange={(e) => setEnergy(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={hasBlocker}
            onChange={(e) => setHasBlocker(e.target.checked)}
          />
          I have a blocker
        </label>

        <div>
          <label className="block font-medium mb-1">Note (optional)</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
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
