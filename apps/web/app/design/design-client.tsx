"use client";

import { useState } from "react";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { NumberTicker } from "@/components/sera/number-ticker";
import { Marquee } from "@/components/sera/marquee";
import { TranscriptBubble } from "@/components/daisy/transcript-bubble";

/* ── Token swatch helpers ─────────────────────────────────────────────── */

interface SwatchProps {
  cssVar: string;
  label: string;
  hex: string;
}

function ColorSwatch({ cssVar, label, hex }: SwatchProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div
        className="h-14 w-full rounded-xl border border-border shadow-sm"
        style={{ background: `var(${cssVar})` }}
        aria-label={`Color: ${label}`}
      />
      <div>
        <p className="text-xs font-semibold text-ink">{label}</p>
        <p className="font-mono text-[10px] text-muted">{cssVar}</p>
        <p className="font-mono text-[10px] text-muted">{hex}</p>
      </div>
    </div>
  );
}

/* ── Section wrapper ──────────────────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="font-display text-2xl font-bold text-ink border-b border-border pb-2">
        {title}
      </h2>
      {children}
    </section>
  );
}

/* ── Main client component ────────────────────────────────────────────── */

/**
 * /design — Visual QA page for Pakka.
 * Showcases design tokens, type scale, buttons, cards, badges,
 * the PakkaStamp, a Sera UI component, and a daisyUI chat bubble.
 */
export function DesignPageClient() {
  const [stampVisible, setStampVisible] = useState(false);

  const colorTokens: SwatchProps[] = [
    { cssVar: "--background", label: "Background", hex: "#FBF9F4" },
    { cssVar: "--surface", label: "Surface", hex: "#FFFFFF" },
    { cssVar: "--surface-2", label: "Surface 2", hex: "#F4F0E8" },
    { cssVar: "--ink", label: "Ink", hex: "#15130F" },
    { cssVar: "--muted", label: "Muted", hex: "#6B6558" },
    { cssVar: "--border", label: "Border", hex: "#E8E2D5" },
    { cssVar: "--primary", label: "Primary (Saffron)", hex: "#FF9F1C" },
    { cssVar: "--success", label: "Success (Pakka Green)", hex: "#12805C" },
    { cssVar: "--warning", label: "Warning", hex: "#D97706" },
    { cssVar: "--danger", label: "Danger", hex: "#D64545" },
    { cssVar: "--info", label: "Info", hex: "#3B5BDB" },
  ];

  const marqueeItems = [
    "Booking confirmed ✓",
    "Nali theek ho gayi 🔧",
    "Payment pakka 💰",
    "Plumber dispatch hoga ⚡",
    "Geyser repair booked ✓",
    "Har call ka jawab 📞",
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <header className="sticky top-0 z-50 glass border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <h1 className="font-display text-xl font-bold text-ink">
            Pakka <span className="text-primary">✓</span>
            <span className="ml-2 text-sm font-normal text-muted">Design QA</span>
          </h1>
          <span className="rounded-full border border-border px-3 py-1 text-xs text-muted">
            Phase 0
          </span>
        </div>
      </header>

      {/* Marquee demo */}
      <div className="border-b border-border py-3">
        <Marquee
          items={marqueeItems.map((item) => (
            <span key={item} className="rounded-full border border-border bg-surface px-4 py-1.5 text-sm text-ink shadow-sm">
              {item}
            </span>
          ))}
          duration={25}
        />
      </div>

      <main className="mx-auto max-w-5xl space-y-16 px-4 py-12">

        {/* ── Color Tokens ──────────────────────────────── */}
        <Section title="Color Tokens">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {colorTokens.map((t) => (
              <ColorSwatch key={t.cssVar} {...t} />
            ))}
          </div>
        </Section>

        {/* ── Typography Scale ──────────────────────────── */}
        <Section title="Typography Scale">
          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted mb-1">Display / Bricolage Grotesque</p>
              <p className="font-display text-5xl font-extrabold text-ink leading-tight">
                हर missed call का cost है
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Heading / Bricolage Grotesque Bold</p>
              <p className="font-display text-3xl font-bold text-ink">
                Pakka picks up, books the job.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Body / Geist</p>
              <p className="font-sans text-base text-ink">
                A voice assistant for small Indian service businesses. Answers in Hinglish, 24/7.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Muted / Geist</p>
              <p className="font-sans text-sm text-muted">
                Booking confirmed — Rohit Plumber, shaam 5 baje.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Mono / JetBrains Mono (transcript)</p>
              <p className="font-mono text-sm text-ink bg-surface-2 rounded-lg px-4 py-3 border border-border">
                {"[caller]: Bhai, geyser kharab hai. Subah se nahi chal raha."}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Devanagari / Noto Sans Devanagari</p>
              <p className="font-devanagari text-xl text-ink">
                पक्की बुकिंग — हर मिस्ड कॉल का जवाब
              </p>
            </div>
          </div>
        </Section>

        {/* ── Buttons ───────────────────────────────────── */}
        <Section title="Buttons">
          <div className="flex flex-wrap gap-3">
            {/* Primary */}
            <button className="rounded-[var(--radius)] bg-primary px-6 py-2.5 text-sm font-semibold text-primary-fg transition-colors hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary min-h-[44px]">
              Book Now
            </button>
            {/* Secondary */}
            <button className="rounded-[var(--radius)] border border-border bg-surface px-6 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary min-h-[44px]">
              View Jobs
            </button>
            {/* Success */}
            <button className="rounded-[var(--radius)] bg-success px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-success min-h-[44px]">
              Confirm ✓
            </button>
            {/* Danger */}
            <button className="rounded-[var(--radius)] bg-danger px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-danger min-h-[44px]">
              Decline
            </button>
            {/* Ghost */}
            <button className="rounded-[var(--radius)] px-6 py-2.5 text-sm font-semibold text-muted transition-colors hover:text-ink hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary min-h-[44px]">
              Cancel
            </button>
          </div>
        </Section>

        {/* ── Cards ────────────────────────────────────── */}
        <Section title="Cards">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* Job Card */}
            <div className="relative rounded-[var(--radius-lg)] border border-border bg-surface p-5 shadow-sm">
              <div className="absolute -top-2 -right-2">
                <PakkaStamp size="sm" visible />
              </div>
              <p className="text-xs text-muted">Job #PK-1042</p>
              <p className="mt-1 font-display text-lg font-semibold text-ink">Geyser Repair</p>
              <p className="mt-1 text-sm text-muted">Sector 12, Rohini · Shaam 5 baje</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="rounded-full bg-success/10 border border-success/20 px-2.5 py-0.5 text-xs font-semibold text-success">
                  Pakka ✓
                </span>
                <span className="rounded-full bg-surface-2 border border-border px-2.5 py-0.5 text-xs text-muted">
                  ₹350–500
                </span>
              </div>
            </div>

            {/* Stat Card */}
            <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-5 shadow-sm">
              <p className="text-xs font-medium text-muted uppercase tracking-wider">Calls Answered</p>
              <p className="mt-2 font-display text-4xl font-bold text-ink">
                <NumberTicker value={247} suffix="+" />
              </p>
              <p className="mt-1 text-sm text-success font-medium">↑ 12% this week</p>
            </div>

            {/* Glow card */}
            <div className="relative rounded-[var(--radius-lg)] border border-primary/30 bg-surface p-5 shadow-sm overflow-hidden glow-saffron">
              <div className="relative z-10">
                <p className="text-xs text-muted">Revenue protected</p>
                <p className="mt-2 font-display text-4xl font-bold text-primary">
                  <NumberTicker value={18450} prefix="₹" />
                </p>
                <p className="mt-1 text-sm text-muted">48 missed → booked this month</p>
              </div>
            </div>
          </div>
        </Section>

        {/* ── Badges ───────────────────────────────────── */}
        <Section title="Badges">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-xs font-semibold text-primary">
              Primary
            </span>
            <span className="rounded-full bg-success/10 border border-success/20 px-3 py-1 text-xs font-semibold text-success">
              Pakka ✓
            </span>
            <span className="rounded-full bg-warning/10 border border-warning/20 px-3 py-1 text-xs font-semibold text-warning">
              Pending
            </span>
            <span className="rounded-full bg-danger/10 border border-danger/20 px-3 py-1 text-xs font-semibold text-danger">
              Failed
            </span>
            <span className="rounded-full bg-info/10 border border-info/20 px-3 py-1 text-xs font-semibold text-info">
              Info
            </span>
            <span className="rounded-full border border-border bg-surface-2 px-3 py-1 text-xs font-semibold text-muted">
              Neutral
            </span>
          </div>
        </Section>

        {/* ── Sera UI: Number Ticker ─────────────────── */}
        <Section title="Sera UI — Number Ticker (re-themed)">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {[
              { label: "Calls today", value: 42, suffix: "" },
              { label: "Jobs booked", value: 38, suffix: "" },
              { label: "Collection rate", value: 91, suffix: "%" },
              { label: "Avg response", value: 1.4, suffix: "s", decimalPlaces: 1 },
            ].map((stat) => (
              <div key={stat.label} className="rounded-[var(--radius)] border border-border bg-surface p-4 shadow-sm text-center">
                <p className="font-display text-3xl font-bold text-ink">
                  <NumberTicker value={stat.value} suffix={stat.suffix} decimalPlaces={stat.decimalPlaces ?? 0} />
                </p>
                <p className="mt-1 text-xs text-muted">{stat.label}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted mt-2">
            Note: Original Sera UI uses dark text colors. Re-themed to use <code className="font-mono">var(--ink)</code> and <code className="font-mono">var(--muted)</code>.
          </p>
        </Section>

        {/* ── PAKKA ✓ Stamp ─────────────────────────── */}
        <Section title="Signature Element — PAKKA ✓ Stamp">
          <div className="flex flex-wrap items-center gap-8">
            {/* Interactive trigger */}
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={() => setStampVisible((v) => !v)}
                className="rounded-[var(--radius)] bg-primary px-6 py-2.5 text-sm font-semibold text-primary-fg transition-colors hover:bg-primary-hover min-h-[44px]"
                aria-label={stampVisible ? "Hide stamp" : "Show stamp animation"}
              >
                {stampVisible ? "Reset" : "Trigger Stamp ✓"}
              </button>
              <PakkaStamp size="lg" variant="success" visible={stampVisible} />
            </div>

            {/* Static sizes for reference */}
            <div className="flex items-end gap-6">
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="sm" variant="primary" />
                <span className="text-xs text-muted">sm / primary</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="md" variant="success" />
                <span className="text-xs text-muted">md / success</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="lg" variant="primary" />
                <span className="text-xs text-muted">lg / primary</span>
              </div>
            </div>
          </div>
        </Section>

        {/* ── daisyUI: Chat Bubbles (transcript) ─────── */}
        <Section title="daisyUI — Chat Bubbles (Transcript, re-themed)">
          <div className="rounded-[var(--radius-lg)] border border-border bg-surface-2 p-4 space-y-1">
            <TranscriptBubble
              role="caller"
              text="Bhai, geyser kharab hai. Subah se nahi chal raha."
              timestamp="10:14 AM"
            />
            <TranscriptBubble
              role="assistant"
              text="Namaste! Main Pakka ki digital sahayak hoon. Koi baat nahi — main aapki booking abhi kar deti hoon. Kya problem hai exactly?"
              timestamp="10:14 AM"
            />
            <TranscriptBubble
              role="caller"
              text="Pani garam nahi ho raha. Pilot light bhi nahi jal rahi."
              timestamp="10:15 AM"
            />
            <TranscriptBubble
              role="assistant"
              text="Theek hai! Geyser pilot light issue — estimated cost do sau se teen sau rupaye. Aapka address batayein?"
              timestamp="10:15 AM"
              isPartial
            />
          </div>
          <p className="text-xs text-muted mt-2">
            Note: daisyUI installed with <code className="font-mono">prefix: &quot;daisy-&quot;</code>. 
            Bubble colors overridden with Pakka token variables. No daisyUI theme variables active.
          </p>
        </Section>

        {/* ── Sera UI: Marquee (shown at page top) ──── */}
        <Section title="Sera UI — Marquee (re-themed)">
          <div className="rounded-[var(--radius-lg)] border border-border overflow-hidden">
            <Marquee
              items={[
                "Calls answered 24/7",
                "Hinglish support",
                "Technician dispatch",
                "Payment follow-up",
                "Price list config",
                "DEMO mode",
              ].map((item) => (
                <span key={item} className="rounded-full border border-border bg-surface px-4 py-2 text-sm font-medium text-ink">
                  {item}
                </span>
              ))}
              direction="left"
              duration={20}
            />
          </div>
          <p className="text-xs text-muted mt-2">
            Note: Sera UI Marquee re-themed — gradient fade uses <code className="font-mono">var(--background)</code> instead of dark hard-coded colors.
          </p>
        </Section>

        {/* ── Noise Texture ─────────────────────────── */}
        <Section title="Noise Texture + Glass Utilities">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="noise-bg rounded-[var(--radius-lg)] border border-border bg-surface-2 p-6 shadow-sm">
              <p className="font-semibold text-ink">.noise-bg</p>
              <p className="text-sm text-muted mt-1">Subtle noise texture overlay via CSS</p>
            </div>
            <div className="glass rounded-[var(--radius-lg)] p-6">
              <p className="font-semibold text-ink">.glass</p>
              <p className="text-sm text-muted mt-1">Backdrop blur + semi-transparent surface</p>
            </div>
          </div>
        </Section>

        {/* Footer */}
        <footer className="text-center pt-8 pb-4">
          <p className="text-xs text-muted">
            Pakka Design QA · Phase 0 Foundation · Built for Gnani AI Internship Challenge
          </p>
        </footer>
      </main>
    </div>
  );
}

