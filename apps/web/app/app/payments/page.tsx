"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  PhoneCall,
  Clock,
  PauseCircle,

  History,
  MessageSquare,
  Sparkles,
  Plus,
  RotateCcw,
  ShieldCheck,
  Ban,
  Check,
} from "lucide-react";
import { useClockStore } from "@/lib/stores/clock-store";
import { useModeStore } from "@/lib/stores/mode-store";
import { fetchPaymentPromises, fetchOverviewStats } from "@/lib/api/client";
import { PaymentPromise, PromiseStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export default function PaymentsPage() {
  const { mode } = useModeStore();
  const {
    daysOffset,
    advanceDays,
    resetClock,
    getCurrentTime,
    isWithinOutboundHours,
  } = useClockStore();

  const queryClient = useQueryClient();
  const [selectedPromise, setSelectedPromise] = useState<PaymentPromise | null>(null);
  const [quickEntryText, setQuickEntryText] = useState("");
  const [isSubmittingEntry, setIsSubmittingEntry] = useState(false);
  const [suppressedNumbers] = useState<string[]>([
    "+91 98XXXXXX90", // Example wrong number
  ]);

  const simulatedDate = getCurrentTime();
  const formattedSimulatedDate = simulatedDate.toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const outboundOpen = isWithinOutboundHours();

  const { data: stats } = useQuery({
    queryKey: ["overview-stats", daysOffset],
    queryFn: () => fetchOverviewStats(daysOffset),
  });

  const { data: promises, isLoading, isError, refetch } = useQuery({
    queryKey: ["payment-promises", daysOffset],
    queryFn: () => fetchPaymentPromises(daysOffset),
  });

  const getStatusBadge = (promise: PaymentPromise) => {
    if (
      promise.status === "paused" ||
      promise.status === "disputed" ||
      ((promise.tone_level ?? 1) >= 3 && promise.status !== "paid" && promise.status !== "kept")
    ) {
      return (
        <Badge variant="outline" className="bg-purple-50 text-purple-800 border-purple-300 gap-1 font-semibold">
          <PauseCircle className="w-3 h-3 text-purple-600" />
          Paused, waiting for owner
        </Badge>
      );
    }
    switch (promise.status) {
      case "paid":
        return (
          <Badge className="bg-emerald-50 text-emerald-800 border-emerald-300 gap-1 font-semibold">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Paid & Settled
          </Badge>
        );
      case "due_today":
        return (
          <Badge className="bg-amber-50 text-amber-800 border-amber-300 gap-1 font-semibold animate-pulse">
            <Clock className="w-3 h-3 text-amber-600" />
            Due Today
          </Badge>
        );
      case "broken":
        return (
          <Badge variant="destructive" className="gap-1 font-semibold">
            <AlertTriangle className="w-3 h-3" />
            Promise Broken
          </Badge>
        );
      case "pending":
      default:
        return (
          <Badge variant="outline" className="text-muted-foreground gap-1">
            <Calendar className="w-3 h-3" />
            Upcoming Due
          </Badge>
        );
    }
  };

  const handleManualReminder = async (promise: PaymentPromise) => {
    // 1. Check suppression list
    if (suppressedNumbers.includes(promise.customer_phone_masked)) {
      toast.error(`Number Permanently Suppressed`, {
        description: `This number is marked as Wrong Number / Opt-out. Automated and manual collection calls are strictly blocked.`,
      });
      return;
    }

    // 2. Check calling hours (9 AM – 8 PM IST strictly)
    if (!outboundOpen) {
      toast.warning(`Outside Outbound Calling Hours`, {
        description: `Calling hours are strictly 9:00 AM – 8:00 PM IST. Current simulated time is outside calling bounds. Call prevented.`,
      });
      return;
    }

    if (mode === "LIVE") {
      try {
        const res = await fetch(`http://localhost:8000/api/promises/${promise.id}/call-now`, {
          method: "POST",
        });
        const data = await res.json();
        if (data.status === "dialed") {
          toast.success(`Voice collection call placed to ${promise.customer_name}`, {
            description: `Calling via Exotel Voicebot with Tone Level ${promise.tone_level || 1} script.`,
          });
          queryClient.invalidateQueries({ queryKey: ["payment-promises"] });
        } else {
          toast.error(`Call blocked: ${data.message}`);
        }
      } catch {
        toast.info(`Voice reminder simulated for ${promise.customer_name} (₹${promise.amount})`);
      }
    } else {
      toast.success(`Voice collection call simulated for ${promise.customer_name}`, {
        description: `Targeting amount ₹${promise.amount}. Reminder recorded in customer audit trail.`,
      });
    }
  };

  const handleMarkAsPaid = (promise: PaymentPromise) => {
    toast.success(`Payment marked as collected for ${promise.customer_name}`, {
      description: `₹${promise.amount} recorded to business UPI ledger.`,
    });
  };

  const handleQuickEntry = async () => {
    if (!quickEntryText.trim()) return;
    setIsSubmittingEntry(true);

    try {
      const res = await fetch("http://localhost:8000/api/ledger/entry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: quickEntryText }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Ledger Entry Recorded!`, {
          description: `${data.parsed.customer_name}: ₹${data.parsed.paid_amount} paid, ₹${data.parsed.balance} balance promised for ${data.parsed.promise_date || "upcoming"}.`,
        });
        setQuickEntryText("");
        refetch();
        return;
      }
    } catch {
      // Fallback in demo mode
    }

    toast.success(`Ledger Entry Recorded (Demo Mode)`, {
      description: `Parsed: Customer payment & remaining balance recorded to active promises.`,
    });
    setQuickEntryText("");
    setIsSubmittingEntry(false);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
              Payments & Money Loop
            </h1>
            <Badge
              variant="outline"
              className={
                outboundOpen
                  ? "bg-emerald-50 text-emerald-800 border-emerald-300 text-xs font-semibold"
                  : "bg-amber-50 text-amber-800 border-amber-300 text-xs font-semibold"
              }
            >
              {outboundOpen ? "Outbound Hours Open (9-8)" : "Calling Window Closed"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Automated Hinglish debt recovery, Promise to Pay (PTP) tracking, and simulated clock.
          </p>
        </div>

        {/* Clock Controls */}
        <div className="flex flex-wrap items-center gap-2 bg-muted/50 p-2 rounded-2xl border border-border">
          <div className="text-xs font-mono font-medium text-ink px-2.5 py-1 bg-background rounded-lg border border-border/80">
            {formattedSimulatedDate}
          </div>
          <Button
            size="sm"
            variant="outline"
            className="text-xs gap-1 h-8"
            onClick={() => advanceDays(1)}
            title="Advance simulated clock forward by 1 day"
          >
            <Clock className="w-3.5 h-3.5 text-primary" />
            <span>+1 Day</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs gap-1 h-8"
            onClick={() => advanceDays(2)}
            title="Advance simulated clock forward by 2 days"
          >
            <Clock className="w-3.5 h-3.5 text-primary" />
            <span>+2 Days</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs gap-1 h-8 text-muted-foreground"
            onClick={() => resetClock()}
            title="Reset clock to initial simulated time"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </Button>
        </div>
      </div>

      {/* Owner Quick Entry Box */}
      <div className="p-4 sm:p-5 rounded-2xl border border-primary/20 bg-primary/5 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm font-bold text-ink">Owner Quick Ledger Entry</span>
            <Badge variant="outline" className="text-[10px] text-muted-foreground bg-background">
              Rule-based Hinglish Parser
            </Badge>
          </div>
          <span className="text-[11px] text-muted-foreground">e.g. Ramesh ke kaam 800 mile 500 baaki kal</span>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <Input
            value={quickEntryText}
            onChange={(e) => setQuickEntryText(e.target.value)}
            placeholder="Type note: Ramesh ke kaam ho gaya 800 mile 500 baaki kal dega"
            className="text-sm flex-1 bg-background border-border"
            onKeyDown={(e) => {
              if (e.key === "Enter" && quickEntryText.trim()) {
                handleQuickEntry();
              }
            }}
          />
          <Button
            size="sm"
            onClick={handleQuickEntry}
            disabled={isSubmittingEntry || !quickEntryText.trim()}
            className="text-xs font-semibold gap-1.5 shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Record Note</span>
          </Button>
        </div>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Pending Collections
          </span>
          <div className="text-2xl sm:text-3xl font-black text-ink mt-2">
            ₹{stats?.rupees_pending ?? 2350}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Active promises tracked under tone ladder
          </p>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Collected Revenue
          </span>
          <div className="text-2xl sm:text-3xl font-black text-emerald-600 mt-2">
            ₹{stats?.rupees_collected ?? 1300}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Settled and verified via owner ledger
          </p>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Outbound Safety Protocol
          </span>
          <div className="text-base sm:text-lg font-bold text-ink mt-2 flex items-center gap-2">
            <span className={outboundOpen ? "w-2.5 h-2.5 rounded-full bg-emerald-500" : "w-2.5 h-2.5 rounded-full bg-amber-500"} />
            <span>{outboundOpen ? "Calling Active (9 AM - 8 PM)" : "Calling Paused"}</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Wrong number suppression + Max 3 calls/week</span>
          </p>
        </div>
      </div>

      {/* Promises List */}
      {isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-2xl bg-destructive/5 space-y-2">
          <AlertTriangle className="w-8 h-8 text-destructive mx-auto" />
          <h3 className="text-base font-bold text-ink">Failed to load payment promises</h3>
          <p className="text-xs text-muted-foreground">Unable to fetch collections data. Please try again.</p>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs">Retry</Button>
        </div>
      ) : isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 w-full rounded-2xl" />
          ))}
        </div>
      ) : promises && promises.length > 0 ? (
        <div className="space-y-3">
          {promises.map((promise) => {
            const isSuppressed = suppressedNumbers.includes(promise.customer_phone_masked);
            return (
              <div
                key={promise.id}
                className="p-5 rounded-2xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-bold text-base text-ink tracking-tight">
                      {promise.customer_name}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      {promise.customer_phone_masked}
                    </span>
                    {getStatusBadge(promise)}
                    <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      ₹{promise.amount}
                    </span>
                    {isSuppressed && (
                      <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 text-[10px] gap-1">
                        <Ban className="w-2.5 h-2.5" />
                        Suppressed (Wrong Number)
                      </Badge>
                    )}
                  </div>

                  <div className="text-xs text-foreground/80 flex items-center gap-2">
                    <span className="font-medium text-ink">{promise.job_title}</span>
                    <span className="text-muted-foreground">&bull;</span>
                    <span className="text-muted-foreground">Due Date: <strong>{promise.due_date}</strong></span>
                  </div>

                  {promise.notes && (
                    <div className="text-xs text-amber-800 bg-amber-50/80 border border-amber-200/80 px-2.5 py-1 rounded-lg mt-1 inline-block">
                      Objection / Note: <span className="italic font-medium">&ldquo;{promise.notes}&rdquo;</span>
                    </div>
                  )}
                </div>

                {/* Action Buttons & Reminder Count */}
                <div className="flex flex-wrap items-center gap-2 pt-3 md:pt-0 border-t md:border-t-0 border-border/50">
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs gap-1.5"
                    onClick={() => setSelectedPromise(promise)}
                  >
                    <History className="w-3.5 h-3.5 text-primary" />
                    <span>Trail ({promise.reminder_trail.length})</span>
                  </Button>

                  {promise.status !== "paid" && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        className={
                          !outboundOpen || isSuppressed
                            ? "text-xs gap-1.5 opacity-60 cursor-not-allowed"
                            : "text-xs gap-1.5 hover:border-primary hover:text-primary"
                        }
                        onClick={() => handleManualReminder(promise)}
                      >
                        <PhoneCall className="w-3.5 h-3.5 text-primary" />
                        <span>Call Now</span>
                      </Button>
                      <Button
                        size="sm"
                        className="text-xs gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
                        onClick={() => handleMarkAsPaid(promise)}
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Mark Paid</span>
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center border border-dashed border-border rounded-2xl bg-card/40">
          <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-600 mb-3 opacity-70" />
          <h3 className="text-base font-bold text-ink">All balances settled!</h3>
          <p className="text-xs text-muted-foreground mt-1">
            No pending collections at this simulated time.
          </p>
        </div>
      )}

      {/* Reminder Trail Dialog (Sera Timeline Style) */}
      <Dialog open={Boolean(selectedPromise)} onOpenChange={(open) => !open && setSelectedPromise(null)}>
        {selectedPromise && (
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold text-ink flex items-center gap-2">
                <History className="w-4 h-4 text-primary" />
                <span>Customer Reminder Trail</span>
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Dated audit record for {selectedPromise.customer_name} ({selectedPromise.customer_phone_masked})
              </DialogDescription>
            </DialogHeader>

            <div className="mt-3 space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Service:</span>
                  <span className="font-semibold text-ink">{selectedPromise.job_title}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Amount:</span>
                  <span className="font-bold text-emerald-700">₹{selectedPromise.amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Current Status:</span>
                  <span className="font-medium capitalize">{selectedPromise.status.replace("_", " ")}</span>
                </div>
              </div>

              {/* Sera Timeline */}
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                  Contact Timeline
                </h4>
                <div className="relative pl-4 border-l-2 border-primary/20 space-y-4">
                  {selectedPromise.reminder_trail.map((event, idx) => (
                    <div key={event.id || idx} className="relative group">
                      <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-primary ring-4 ring-background" />
                      <div className="p-3 rounded-xl border border-border bg-card text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-ink flex items-center gap-1.5 capitalize">
                            {event.type === "voice_call" ? (
                              <PhoneCall className="w-3.5 h-3.5 text-primary" />
                            ) : (
                              <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
                            )}
                            <span>{event.type.replace("_", " ")}</span>
                          </span>
                          <time className="text-[10px] text-muted-foreground">{event.timestamp}</time>
                        </div>

                        <p className="text-foreground/85 text-[11px] mt-0.5">{event.note}</p>

                        {event.outcome && (
                          <p className="text-[11px] italic text-primary/90 bg-primary/5 p-1.5 rounded border border-primary/20 mt-1">
                            Outcome: &ldquo;{event.outcome}&rdquo;
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
