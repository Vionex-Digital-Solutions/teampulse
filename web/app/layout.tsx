import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "TeamPulse",
  description: "Team health & engagement — Vionex onboarding project",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <nav className="bg-navy text-white px-6 py-4 flex items-center gap-6">
            <Link href="/" className="font-bold text-lg">
              TeamPulse
            </Link>
            <Link href="/pulse" className="hover:text-accent">
              Pulse
            </Link>
            <Link href="/standup" className="hover:text-accent">
              Standup
            </Link>
            <Link href="/kudos" className="hover:text-accent">
              Kudos
            </Link>
          </nav>
          <main className="max-w-3xl mx-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
