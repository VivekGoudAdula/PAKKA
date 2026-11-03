"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  PhoneCall,
  CalendarCheck,
  Clock,
  IndianRupee,
  ShieldCheck,
  ArrowRight,
  MapPin,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { useClockStore } from "@/lib/stores/clock-store";
import { fetchOverviewStats, fetchJobs } from "@/lib/api/client";
import { NumberTicker } from "@/components/sera/number-ticker";
import { Timeline, TimelineItem } from "@/components/sera/timeline";
import { BentoCard } from "@/components/sera/bento-grid";
import { SpotlightCard } from "@/components/sera/spotlight-card";
import { AnimatedBadge } from "@/components/sera/animated-badge";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const OVERVIEW_TIMELINE_ITEMS: TimelineItem[] = [
  {
    id: "tl-1",
    time: "10:24 AM",
    title: "Call Answered: Tap leakage & pipe replacement",
    description: "Caller: +91 98XXXXXX11 • Landmark: Pocket 1, Mayur Vihar",
    badge: "Booked",
    type: "booking",
  },
  {
    id: "tl-2",
    time: "10:15 AM",
    title: "Technician Accepted: Ramesh Kumar",
    description: "Spoken response: 'haan, pakka, 2 baje pohoch jaunga'",
    badge: "Dispatched",
    type: "dispatch",
  },
  {
    id: "tl-3",
    time: "09:48 AM",
    title: "Payment Promise Registered: ₹450",
    description: "Geyser repair • Promised tomorrow morning via UPI",
    badge: "Promise",
    type: "payment",
  },
  {
    id: "tl-4",
    time: "09:05 AM",
    title: "Outbound Reminder Triggered",
    description: "Chased pending ₹350 from yesterday • Caller requested evening callback",
    badge: "Reminder",
    type: "reminder",
  },
];

export default function OverviewPage() {
  const { daysOffset } = useClockStore();

  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useQuery({
    queryKey: ["overview-stats", daysOffset],
    queryFn: () => fetchOverviewStats(daysOffset),
  });

  const { data: jobs, isLoading: jobsLoading, isError: jobsError, refetch: refetchJobs } = useQuery({
    queryKey: ["recent-jobs"],
    queryFn: fetchJobs,
  });

  const recentJobs = jobs?.slice(0, 4) || [];
  const hasError = statsError || jobsError;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Business Overview
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Every missed call has a cost. Pakka picks up, books, dispatches, and collects.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/app/calls">
            <Button variant="outline" size="sm" className="gap-2">
              <PhoneCall className="w-4 h-4 text-primary" />
              <span>View All Calls</span>
            </Button>
          </Link>
          <Link href="/app/jobs">
            <Button size="sm" className="gap-2 bg-primary hover:bg-primary/90 text-white font-semibold">
              <span>Jobs Board</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>

      {hasError && (
        <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Some dashboard data could not be refreshed.</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              refetchStats();
              refetchJobs();
            }}
            className="text-xs"
          >
            Retry
          </Button>
        </div>
      )}

      {/* 4 Hero Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Calls Answered */}
        <SpotlightCard className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Calls Answered
            </span>
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <PhoneCall className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl sm:text-3xl font-black text-ink">
                <NumberTicker value={stats?.calls_answered ?? 10} />
              </div>
            )}
            <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
              <span className="text-success font-semibold">100%</span> picked up 24/7
            </p>
          </div>
        </SpotlightCard>

        {/* Jobs Booked */}
        <SpotlightCard className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Jobs Booked
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600">
              <CalendarCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl sm:text-3xl font-black text-ink">
                <NumberTicker value={stats?.jobs_booked ?? 10} />
              </div>
            )}
            <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
              <span className="text-emerald-600 font-semibold">83%</span> conversion rate
            </p>
          </div>
        </SpotlightCard>

        {/* Rupees Pending */}
        <SpotlightCard className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Pending Chase
            </span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-600">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl sm:text-3xl font-black text-ink">
                <NumberTicker value={stats?.rupees_pending ?? 2350} prefix="₹" />
              </div>
            )}
            <p className="text-[11px] text-muted-foreground mt-1">
              Chased within 9 AM – 8 PM
            </p>
          </div>
        </SpotlightCard>

        {/* Rupees Collected */}
        <SpotlightCard className="p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Money Collected
            </span>
            <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center text-success">
              <IndianRupee className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            {statsLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl sm:text-3xl font-black text-success">
                <NumberTicker value={stats?.rupees_collected ?? 1300} prefix="₹" />
              </div>
            )}
            <p className="text-[11px] text-muted-foreground mt-1">
              Direct to owner UPI
            </p>
          </div>
        </SpotlightCard>
      </div>

      {/* Live Now Card + Bento Recovery Tile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Active Call Card */}
        <div className="lg:col-span-2 rounded-2xl border border-primary/30 bg-gradient-to-br from-card via-card to-primary/5 p-5 sm:p-6 relative overflow-hidden shadow-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AnimatedBadge label="LIVE CALL" variant="success" pulse />
              <span className="text-xs text-muted-foreground font-mono">01:42</span>
            </div>
            <span className="text-xs bg-muted/80 text-ink/80 px-2.5 py-1 rounded-full font-medium">
              Prisma v3.0 STT &bull; Timbre TTS
            </span>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold text-muted-foreground">Inbound Customer</p>
              <p className="text-lg font-bold text-ink tracking-tight">
                {stats?.active_call.caller_masked ?? "+91 98XXXXXX88"}
              </p>
              <p className="text-sm text-foreground/80 mt-1">
                State: <span className="font-medium text-primary">{stats?.active_call.state}</span>
              </p>
            </div>

            {/* Pulsing Audio waveform visualizer */}
            <div className="flex items-center gap-1 self-start sm:self-center h-10 px-4 py-2 bg-background/80 rounded-xl border border-border">
              {[40, 75, 25, 90, 60, 85, 30, 95, 50, 70, 45, 80].map((h, i) => (
                <span
                  key={i}
                  className="w-1 bg-primary rounded-full animate-pulse"
                  style={{
                    height: `${h}%`,
                    animationDelay: `${i * 90}ms`,
                  }}
                />
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Digital assistant identity announced</span>
            </span>
            <span className="italic">&ldquo;Main Ramesh bhai ki digital sahayak...&rdquo;</span>
          </div>
        </div>

        {/* Missed Calls Recovered Bento Tile */}
        <BentoCard
          title="Missed Calls Recovered"
          subtitle="Every incoming customer call was captured and routed without owner intervention."
          badge={<Badge variant="outline" className="border-emerald-500/40 text-emerald-700 bg-emerald-50 text-[10px]">100% Retained</Badge>}
          className="flex flex-col justify-between"
        >
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Jobs saved from missed calls:</span>
              <span className="font-bold text-ink">10 jobs</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Estimated revenue protected:</span>
              <span className="font-bold text-success">₹3,650</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Wrong numbers stopped:</span>
              <span className="font-bold text-muted-foreground">1 caller</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border/50 text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            <span>Outbound hours strictly 9 AM – 8 PM IST</span>
          </div>
        </BentoCard>
      </div>

      {/* Today's Timeline + Recent Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-ink text-base">Today&apos;s Voice Timeline</h2>
            <span className="text-xs text-muted-foreground">Real-time trace</span>
          </div>
          <Timeline items={OVERVIEW_TIMELINE_ITEMS} />
        </div>

        {/* Recent Jobs with Pakka Stamp */}
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-bold text-ink text-base">Recent Jobs</h2>
              <p className="text-xs text-muted-foreground">Auto-booked via Hinglish phone conversations</p>
            </div>
            <Link href="/app/jobs">
              <Button variant="ghost" size="sm" className="text-xs text-primary hover:text-primary">
                View all ({jobs?.length || 10})
              </Button>
            </Link>
          </div>

          {jobsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-border/70 hover:border-border bg-background/50 hover:bg-background transition-colors gap-3 relative overflow-hidden"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-ink">{job.problem}</span>
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {job.status.replace("_", " ")}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-primary" />
                        <span>{job.landmark_address}</span>
                      </span>
                      <span>Slot: <strong className="text-ink">{job.time_slot}</strong></span>
                      <span>Quote: <strong className="text-emerald-700">{job.price_estimate}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3">
                    <div className="text-right sm:text-right">
                      <span className="text-[11px] text-muted-foreground block">Technician</span>
                      <span className="text-xs font-semibold text-ink">{job.technician_name || "Unassigned"}</span>
                    </div>

                    {/* Pakka Stamp on confirmed jobs */}
                    {job.confirmed_at && (
                      <div className="shrink-0">
                        <PakkaStamp size="sm" visible />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
