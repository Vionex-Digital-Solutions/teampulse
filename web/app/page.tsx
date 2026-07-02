export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-navy">Welcome to TeamPulse</h1>
      <p className="text-slate-600">
        A tiny app where a team posts a daily check-in and gives each other
        kudos. This is the Vionex onboarding project.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
        <a
          href="/pulse"
          className="block rounded-xl border p-5 hover:border-accent transition"
        >
          <h2 className="font-semibold text-navy">Pulse</h2>
          <p className="text-sm text-slate-500">Daily mood + energy check-in.</p>
        </a>
        <a
          href="/standup"
          className="block rounded-xl border p-5 hover:border-accent transition"
        >
          <h2 className="font-semibold text-navy">Standup</h2>
          <p className="text-sm text-slate-500">Yesterday / today / blockers.</p>
        </a>
        <a
          href="/kudos"
          className="block rounded-xl border p-5 hover:border-accent transition"
        >
          <h2 className="font-semibold text-navy">Kudos</h2>
          <p className="text-sm text-slate-500">Recognize a teammate.</p>
        </a>
      </div>
    </div>
  );
}
