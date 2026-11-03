"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  PhoneCall,
  Clock,
  ShieldAlert,
  History,
  MessageSquare,
} from "lucide-react";
import { useClockStore } from "@/lib/stores/clock-store";
import { fetchPaymentPromises, fetchOverviewStats } from "@/lib/api/client";
import { PaymentPromise, PromiseStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export default function PaymentsPage() {
  const { daysOffset, advanceDays } = useClockStore();
  const [selectedPromise, setSelectedPromise] = useState<PaymentPromise | null>(null);

  const { data: stats } = useQuery({
    queryKey: ["overview-stats", daysOffset],
    queryFn: () => fetchOverviewStats(daysOffset),
  });

  const { data: promises, isLoading, isError, refetch } = useQuery({
    queryKey: ["payment-promises", daysOffset],
    queryFn: () => fetchPaymentPromises(daysOffset),
  });

  const getStatusBadge = (status: PromiseStatus) => {
    switch (status) {
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

  const handleManualReminder = (promise: PaymentPromise) => {
    toast.success(`Voice reminder scheduled for ${promise.customer_name}`, {
      description: `Targeting amount ₹${promise.amount}. Calling hours strictly 9 AM – 8 PM IST.`,
    });
  };

  const handleMarkAsPaid = (promise: PaymentPromise) => {
    toast.success(`Payment marked as collected for ${promise.customer_name}`, {
      description: `₹${promise.amount} recorded to business UPI ledger.`,
    });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Payments & Reminder Trail
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Pakka chases outstanding customer payments, records promises, and calls back on promised dates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="text-xs gap-1.5 border-primary/30 text-primary hover:bg-primary/5"
            onClick={() => advanceDays(1)}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Simulate +1 Day Forward</span>
          </Button>
        </div>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Pending Chase
          </span>
          <div className="text-2xl sm:text-3xl font-black text-ink mt-2">
            ₹{stats?.rupees_pending ?? 2350}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Active promises under automated follow-up
          </p>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Collected Revenue
          </span>
          <div className="text-2xl sm:text-3xl font-black text-success mt-2">
            ₹{stats?.rupees_collected ?? 1300}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Verified received via owner QR / UPI
          </p>
        </div>

        <div className="p-4 sm:p-5 rounded-2xl border border-border bg-card shadow-xs">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
            Outbound Rules
          </span>
          <div className="text-base sm:text-lg font-bold text-ink mt-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>9 AM – 8 PM IST Only</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
            <span>Immediate stop on &ldquo;wrong number&rdquo;</span>
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
          {promises.map((promise) => (
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
                  {getStatusBadge(promise.status)}
                  <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    ₹{promise.amount}
                  </span>
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
                      className="text-xs gap-1.5 hover:border-primary hover:text-primary"
                      onClick={() => handleManualReminder(promise)}
                    >
                      <PhoneCall className="w-3.5 h-3.5 text-primary" />
                      <span>Trigger Call</span>
                    </Button>
                    <Button
                      size="sm"
                      className="text-xs gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
                      onClick={() => handleMarkAsPaid(promise)}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Mark Paid</span>
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
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

      {/* Reminder Trail Dialog */}
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

              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                  Contact Timeline
                </h4>
                {selectedPromise.reminder_trail.map((event) => (
                  <div
                    key={event.id}
                    className="p-3 rounded-xl border border-border bg-card text-xs space-y-1"
                  >
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
                ))}
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
