import Link from "next/link";

/**
 * Root index page — minimal placeholder for Phase 0.
 * The landing page is built in Phase 2.
 */
export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4">
      <div className="text-center">
        <h1 className="font-display text-5xl font-bold text-ink">
          Pakka <span className="text-primary">✓</span>
        </h1>
        <p className="mt-2 font-sans text-lg text-muted">
          Every missed call has a cost.
        </p>
      </div>

      <nav className="flex flex-col items-center gap-3 sm:flex-row">
        <Link
          href="/design"
          className="rounded-md bg-primary px-6 py-2.5 text-sm font-semibold text-primary-fg transition-colors hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          Design QA →
        </Link>
      </nav>

      <p className="text-xs text-muted">Phase 0 — Foundation scaffold</p>
    </main>
  );
}
