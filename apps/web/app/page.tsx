import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  PhoneCall,
  Play,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserCheck,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PakkaLogo } from "@/components/pakka/pakka-logo";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { cn } from "@/lib/utils";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-ink selection:bg-primary/20 selection:text-ink">
      {/* ── Top Header Bar ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <PakkaLogo size="md" />
          </Link>

          <nav className="hidden items-center gap-6 md:flex">
            <a
              href="#how-it-works"
              className="text-sm font-medium text-muted transition-colors hover:text-ink"
            >
              How It Works
            </a>
            <a
              href="#architecture"
              className="text-sm font-medium text-muted transition-colors hover:text-ink"
            >
              Gnani AI Stack
            </a>
            <a
              href="#trust"
              className="text-sm font-medium text-muted transition-colors hover:text-ink"
            >
              Safety & Trust
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/app/live?demo=true"
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "hidden sm:inline-flex text-muted hover:text-ink"
              )}
            >
              Watch Demo
            </Link>
            <Link
              href="/app"
              className={cn(
                buttonVariants({ size: "sm" }),
                "gap-2 bg-primary hover:bg-primary/90 text-white shadow-sm font-semibold"
              )}
            >
              Enter Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-12 pb-16 sm:pt-20 sm:pb-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center text-center">
            {/* Pill badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3.5 py-1.5 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Built for Indian Trade Businesses · Hindi & Hinglish Voice AI</span>
            </div>

            {/* Main Headline */}
            <h1 className="mt-6 max-w-4xl font-display text-4xl font-extrabold tracking-tight text-ink sm:text-6xl sm:leading-[1.12]">
              Every missed call has a{" "}
              <span className="relative inline-block text-primary">
                cost.
                <span className="absolute -bottom-1 left-0 h-1 w-full rounded bg-primary/30" />
              </span>
            </h1>

            {/* Sub-headline */}
            <p className="mt-6 max-w-2xl text-lg text-muted sm:text-xl leading-relaxed">
              Pakka picks up on the 1st ring, books the job, dispatches the nearest technician, and
              chases overdue payments in polite Hinglish.
            </p>

            {/* Primary Action Buttons */}
            <div className="mt-8 flex flex-col items-center gap-3.5 sm:flex-row">
              <Link
                href="/app/live?demo=true"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "gap-2.5 rounded-xl bg-primary px-7 text-base font-semibold text-white shadow-md hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                )}
              >
                <Play className="h-4 w-4 fill-white" />
                Watch the Demo
              </Link>
              <Link
                href="/app"
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "gap-2 rounded-xl border-border/80 bg-card px-7 text-base font-semibold text-ink shadow-sm hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                )}
              >
                Open Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {/* Micro-guarantees badge strip */}
            <div className="mt-12 flex flex-wrap items-center justify-center gap-4 text-xs font-medium text-muted">
              <span className="flex items-center gap-1.5 rounded-md border border-border bg-card/60 px-3 py-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                100% Deterministic FSM
              </span>
              <span className="flex items-center gap-1.5 rounded-md border border-border bg-card/60 px-3 py-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                Zero Hallucinations in Flow Control
              </span>
              <span className="flex items-center gap-1.5 rounded-md border border-border bg-card/60 px-3 py-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                &lt; 50ms Turn Latency
              </span>
              <span className="flex items-center gap-1.5 rounded-md border border-border bg-card/60 px-3 py-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                Synthetic Demo Data Only
              </span>
            </div>
          </div>

          {/* Hero Mockup Preview Card */}
          <div className="relative mx-auto mt-12 max-w-4xl rounded-2xl border border-border/80 bg-card p-4 shadow-xl sm:p-6">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
                <span className="ml-2 font-mono text-xs text-muted">Pakka Voicebot Telephony Console</span>
              </div>
              <Badge variant="outline" className="gap-1.5 border-primary/30 bg-primary/10 text-primary text-xs">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                DEMO Active
              </Badge>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              {/* Turn 1: Customer */}
              <div className="rounded-xl border border-border/70 bg-background/50 p-3.5 text-sm">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">1. Caller Utterance</span>
                <p className="mt-1 font-medium text-ink">
                  &ldquo;Bhaiya mera geyser paani garam nahi kar raha, Mayur Vihar Pocket 1 se bol raha hoon.&rdquo;
                </p>
                <div className="mt-2.5 flex flex-wrap gap-1 text-[11px] font-mono text-muted">
                  <span className="rounded bg-muted/20 px-1.5 py-0.5">problem: geyser_not_heating</span>
                  <span className="rounded bg-muted/20 px-1.5 py-0.5">area: Mayur Vihar Pocket 1</span>
                </div>
              </div>

              {/* Turn 2: Pakka Bot */}
              <div className="rounded-xl border border-primary/30 bg-primary/5 p-3.5 text-sm">
                <span className="text-xs font-semibold uppercase tracking-wider text-primary">2. Digital Sahayak</span>
                <p className="mt-1 font-medium text-ink">
                  &ldquo;Geyser check karne ka visiting charge ₹450 se ₹750 ke beech hoga. Technician kab bhejoon?&rdquo;
                </p>
                <div className="mt-2.5 flex items-center gap-1.5 text-[11px] font-mono text-muted">
                  <span className="text-success font-semibold">Price floor held</span> · <span>Turn SLA: 12ms</span>
                </div>
              </div>

              {/* Turn 3: Confirmed */}
              <div className="flex flex-col items-center justify-center rounded-xl border border-success/30 bg-success/5 p-3.5 text-center">
                <PakkaStamp size="md" />
                <span className="mt-2 text-xs font-bold text-success">Pakka Job Confirmed</span>
                <span className="text-[11px] text-muted">Auto-dispatched to Imtiaz Ali</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3-Step Service Lifecycle ───────────────────────────────── */}
      <section id="how-it-works" className="border-t border-border/60 bg-muted/20 py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center">
            <span className="text-xs font-bold uppercase tracking-wider text-primary">End-to-End Workflow</span>
            <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
              From First Ring to Payment Cleared
            </h2>
            <p className="mt-3 text-base text-muted max-w-xl mx-auto">
              Pakka handles the entire business operational loop without manual paperwork.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {/* Step 1 */}
            <Card className="border border-border/70 bg-card shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <PhoneCall className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-primary">STEP 01</span>
                  <span className="text-xs text-muted">· Inbound</span>
                </div>
                <h3 className="mt-1 font-display text-xl font-bold text-ink">Answer & Book</h3>
                <p className="mt-2.5 text-sm text-muted leading-relaxed">
                  Picks up on the first ring with mandatory transparent disclosure. Extracts the problem,
                  visiting slot, and landmark address in Hinglish. Quotes upfront and locks the booking.
                </p>
                <div className="mt-4 rounded-lg bg-muted/40 p-2.5 text-xs text-muted font-mono">
                  &ldquo;Namaste, Pakka demo shop ki digital sahayak bol rahi hoon...&rdquo;
                </div>
              </CardContent>
            </Card>

            {/* Step 2 */}
            <Card className="border border-border/70 bg-card shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600">
                  <Wrench className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-blue-600">STEP 02</span>
                  <span className="text-xs text-muted">· Outbound</span>
                </div>
                <h3 className="mt-1 font-display text-xl font-bold text-ink">Auto-Dispatch</h3>
                <p className="mt-2.5 text-sm text-muted leading-relaxed">
                  Ranks technicians by trade specialty (geyser, motor, pipe) and active job load. Places an
                  outbound phone call to confirm acceptance, or automatically re-routes if declined.
                </p>
                <div className="mt-4 rounded-lg bg-muted/40 p-2.5 text-xs text-muted font-mono">
                  &ldquo;Aapke liye naya kaam hai Mayur Vihar mein. Kya aap ja sakte hain?&rdquo;
                </div>
              </CardContent>
            </Card>

            {/* Step 3 */}
            <Card className="border border-border/70 bg-card shadow-sm hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-success/10 text-success">
                  <TrendingUp className="h-6 w-6 stroke-[2.2]" />
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-success">STEP 03</span>
                  <span className="text-xs text-muted">· Collections</span>
                </div>
                <h3 className="mt-1 font-display text-xl font-bold text-ink">Collect & Reconcile</h3>
                <p className="mt-2.5 text-sm text-muted leading-relaxed">
                  Multi-tier tone ladder (Friendly &rarr; Reminder &rarr; Urgent). Captures promise dates,
                  suppresses wrong numbers immediately, and leaves Tone 3 or disputes for owner review.
                </p>
                <div className="mt-4 rounded-lg bg-muted/40 p-2.5 text-xs text-muted font-mono">
                  &ldquo;Aapka ₹500 ka balance baki hai. Aap payment kab tak clear kar denge?&rdquo;
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ── Built on Gnani AI Strip ─────────────────────────────────── */}
      <section id="architecture" className="border-t border-border/60 py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
              <Cpu className="h-3.5 w-3.5" />
              <span>Gnani AI Conversational Voice Stack</span>
            </div>
            <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
              Engineered with Gnani Voice Models
            </h2>
            <p className="mt-2 max-w-xl text-base text-muted">
              Built specifically around Gnani&apos;s real-time streaming speech APIs for Indian languages.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {/* Model 1: Prisma */}
            <div className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-primary">STT ENGINE</span>
                <Badge variant="outline" className="text-[10px] bg-primary/5 text-primary border-primary/20">
                  Prisma v3.0
                </Badge>
              </div>
              <h3 className="mt-3 font-display text-lg font-bold text-ink">Vachana Prisma STT</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Raw PCM linear16 mono audio streamed over WebSocket at 8,000 Hz. Built for real-time
                Hinglish code-mixed recognition and background noise resilience.
              </p>
              <div className="mt-3 text-[11px] font-mono text-muted/80">
                Format: 1024-byte frames · Code-mixed
              </div>
            </div>

            {/* Model 2: Timbre */}
            <div className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-primary">TTS ENGINE</span>
                <Badge variant="outline" className="text-[10px] bg-primary/5 text-primary border-primary/20">
                  Timbre v2.5
                </Badge>
              </div>
              <h3 className="mt-3 font-display text-lg font-bold text-ink">Vachana Timbre TTS</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Expressive Indian female voice (&ldquo;Poorvi&rdquo;) delivering low-latency audio chunks formatted
                specifically for telephony line buffers (&ge; 3200 bytes &amp; multiple of 320).
              </p>
              <div className="mt-3 text-[11px] font-mono text-muted/80">
                Voice: Poorvi · Telephony 8 kHz PCM
              </div>
            </div>

            {/* Model 3: Evon Note */}
            <div className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-muted">EXTRACTION</span>
                <Badge variant="outline" className="text-[10px] bg-muted/20 text-muted border-border">
                  Evon v3.3 Design
                </Badge>
              </div>
              <h3 className="mt-3 font-display text-lg font-bold text-ink">Modular Extractor</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Built behind strict abstract interfaces. Runs an offline deterministic regex extractor (&lt;20ms)
                with verified offline mock and dry-run adapters for Evon slot extraction.
              </p>
              <div className="mt-3 text-[11px] font-mono text-muted/80">
                Truth in engineering · Zero runtime hallucination
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust, Safety & Ethics Section ──────────────────────────── */}
      <section id="trust" className="border-t border-border/60 bg-muted/20 py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center">
            <span className="text-xs font-bold uppercase tracking-wider text-primary">Responsible AI</span>
            <h2 className="mt-2 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
              Trust, Safety &amp; Legal Guardrails
            </h2>
            <p className="mt-3 text-base text-muted max-w-xl mx-auto">
              Engineered with strict customer protection rules baked into every FSM state.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {/* Guardrail 1 */}
            <div className="rounded-xl border border-border/80 bg-card p-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <UserCheck className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-ink">Assistant Identity</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Transparently announces herself as a digital assistant on every single call. Never pretends to be human;
                instantly offers a human owner callback if asked.
              </p>
            </div>

            {/* Guardrail 2 */}
            <div className="rounded-xl border border-border/80 bg-card p-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600">
                <Clock className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-ink">Strict Calling Hours</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Outbound dispatch and payment calls strictly respect owner hours (default 9:00 AM – 8:00 PM IST).
                Inbound calls are answered 24/7.
              </p>
            </div>

            {/* Guardrail 3 */}
            <div className="rounded-xl border border-border/80 bg-card p-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10 text-red-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-ink">Emergency Triage</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Electrical shock, gas leak, fire, or pipe burst flooding immediately interrupts routine booking, delivers
                clear life-safety instructions, and alerts the owner.
              </p>
            </div>

            {/* Guardrail 4 */}
            <div className="rounded-xl border border-border/80 bg-card p-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-600">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-ink">100% Synthetic Privacy</h3>
              <p className="mt-2 text-xs text-muted leading-relaxed">
                Zero real customer data. All seeded names, phone numbers, and addresses in the demo database are
                entirely synthetic. No private credentials in code.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-border/80 bg-card py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex items-center gap-2.5">
              <PakkaLogo size="sm" />
            </div>

            <div className="text-center sm:text-right">
              <p className="text-xs font-medium text-ink">
                Built for the Great Indian AI Internship Challenge by Gnani AI
              </p>
              <p className="mt-1 text-[11px] text-muted">
                Demo data is strictly synthetic. Deadline: Nov 10, 2026.
              </p>
            </div>
          </div>

          <div className="mt-8 border-t border-border/60 pt-6 flex flex-wrap items-center justify-between gap-4 text-xs text-muted">
            <div className="flex items-center gap-4">
              <Link href="/app" className="hover:text-ink transition-colors">
                Dashboard
              </Link>
              <Link href="/app/live" className="hover:text-ink transition-colors">
                Live Console
              </Link>
              <Link href="/app/dispatch" className="hover:text-ink transition-colors">
                Dispatch
              </Link>
              <Link href="/app/payments" className="hover:text-ink transition-colors">
                Payments
              </Link>
              <Link href="/app/metrics" className="hover:text-ink transition-colors">
                Observability
              </Link>
              <Link href="/design" className="hover:text-ink transition-colors">
                Design System QA
              </Link>
            </div>
            <span>© 2026 Pakka · All rights reserved</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
