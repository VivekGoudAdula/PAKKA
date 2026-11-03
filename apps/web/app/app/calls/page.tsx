"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PhoneIncoming,
  Clock,
  MapPin,
  Calendar,
  Play,
  Volume2,
  CheckCircle2,
  Filter,
  AlertCircle,
} from "lucide-react";
import { fetchCalls } from "@/lib/api/client";
import { Call, CallStatus } from "@/lib/types";
import { CallTranscript } from "@/components/pakka/call-transcript";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";

const STATUS_FILTERS = [
  { label: "All Calls", value: "all" },
  { label: "Booked", value: "booked" },
  { label: "Needs Human", value: "needs_human" },
  { label: "Missed", value: "missed" },
];

export default function CallsPage() {
  const [activeFilter, setActiveFilter] = useState("all");
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);

  const { data: calls, isLoading, isError, refetch } = useQuery({
    queryKey: ["calls", activeFilter],
    queryFn: () => fetchCalls(activeFilter),
  });

  const getStatusBadge = (status: CallStatus) => {
    switch (status) {
      case "booked":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border-emerald-300">
            Booked ✓
          </Badge>
        );
      case "needs_human":
        return (
          <Badge className="bg-amber-50 text-amber-700 border-amber-300">
            Needs Human
          </Badge>
        );
      case "missed":
        return (
          <Badge variant="destructive">
            Missed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            {status}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Calls & Transcripts
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            24/7 Inbound Hinglish voice calls captured by Gnani Prisma v3.0 & Timbre.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-muted/60 rounded-xl border border-border overflow-x-auto max-w-full">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setActiveFilter(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                activeFilter === f.value
                  ? "bg-card text-ink shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Calls List */}
      {isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-2xl bg-destructive/5 space-y-2">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
          <h3 className="text-base font-bold text-ink">Failed to load calls</h3>
          <p className="text-xs text-muted-foreground">Unable to fetch call records. Please try again.</p>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs">Retry</Button>
        </div>
      ) : isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-2xl" />
          ))}
        </div>
      ) : calls && calls.length > 0 ? (
        <div className="space-y-3">
          {calls.map((call) => (
            <div
              key={call.id}
              onClick={() => setSelectedCall(call)}
              className="p-4 sm:p-5 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all cursor-pointer shadow-xs hover:shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 overflow-hidden"
            >
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold text-base text-ink tracking-tight">
                    {call.customer_name || "Unknown Customer"}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {call.caller_number_masked}
                  </span>
                  {getStatusBadge(call.status)}
                </div>

                <p className="text-xs text-foreground/85 line-clamp-1">
                  {call.summary}
                </p>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground pt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span>{call.timestamp} ({call.duration_seconds}s)</span>
                  </span>
                  {call.extracted_slots.landmark_address && (
                    <span className="flex items-center gap-1 min-w-0">
                      <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
                      <span className="truncate">{call.extracted_slots.landmark_address}</span>
                    </span>
                  )}
                  {call.extracted_slots.time_slot && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-primary shrink-0" />
                      <span>{call.extracted_slots.time_slot}</span>
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-border/40 shrink-0">
                <div className="text-right hidden sm:block">
                  <span className="text-xs font-semibold text-emerald-700 block">
                    {call.extracted_slots.price_range_min && call.extracted_slots.price_range_max
                      ? `₹${call.extracted_slots.price_range_min} - ₹${call.extracted_slots.price_range_max}`
                      : "Standard rates"}
                  </span>
                  <span className="text-[10px] text-muted-foreground">Extracted Quote</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full sm:w-auto text-xs font-semibold"
                >
                  View Transcript &bull; {call.transcript.length} turns
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-12 text-center border border-dashed border-border rounded-2xl bg-card/40">
          <Filter className="w-8 h-8 mx-auto text-muted-foreground mb-3 opacity-50" />
          <h3 className="text-base font-bold text-ink">No calls found</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            No voice calls match the selected filter &quot;{activeFilter}&quot;. Try switching to &quot;All Calls&quot;.
          </p>
        </div>
      )}

      {/* Transcript Detail Sheet */}
      <Sheet open={Boolean(selectedCall)} onOpenChange={(open) => !open && setSelectedCall(null)}>
        {selectedCall && (
          <SheetContent side="right" className="w-full sm:max-w-xl p-0 flex flex-col h-full bg-card">
            {/* Sheet Header */}
            <SheetHeader className="p-5 border-b border-border bg-muted/20">
              <div className="flex items-center justify-between gap-2">
                <SheetTitle className="text-lg font-bold text-ink flex items-center gap-2">
                  <PhoneIncoming className="w-4 h-4 text-primary" />
                  <span>Call Transcript & Extraction</span>
                </SheetTitle>
                {getStatusBadge(selectedCall.status)}
              </div>
              <SheetDescription className="text-xs text-muted-foreground mt-1">
                {selectedCall.customer_name || "Caller"} &bull; {selectedCall.caller_number_masked} &bull; {selectedCall.timestamp} ({selectedCall.duration_seconds}s)
              </SheetDescription>

              {/* Audio playback indicator */}
              <div className="mt-3 p-3 rounded-xl bg-background border border-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
                    <Play className="w-4 h-4 ml-0.5" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-ink block">Audio not recorded in demo</span>
                    <span className="text-[10px] text-muted-foreground">Telephony audio capture is active only during live Exotel calls.</span>
                  </div>
                </div>
                <Volume2 className="w-4 h-4 text-muted-foreground opacity-50" />
              </div>
            </SheetHeader>

            {/* Extracted Slots Badges */}
            <div className="p-4 border-b border-border bg-primary/5">
              <span className="text-[11px] font-bold text-primary uppercase tracking-wider block mb-2">
                Extracted slots (rule-based)
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 rounded-lg bg-background border border-border">
                  <span className="text-[10px] text-muted-foreground block">Problem</span>
                  <span className="font-semibold text-ink">{selectedCall.extracted_slots.problem || "N/A"}</span>
                </div>
                <div className="p-2 rounded-lg bg-background border border-border">
                  <span className="text-[10px] text-muted-foreground block">Landmark Address</span>
                  <span className="font-semibold text-ink">{selectedCall.extracted_slots.landmark_address || "N/A"}</span>
                </div>
                <div className="p-2 rounded-lg bg-background border border-border">
                  <span className="text-[10px] text-muted-foreground block">Preferred Slot</span>
                  <span className="font-semibold text-ink">{selectedCall.extracted_slots.time_slot || "N/A"}</span>
                </div>
                <div className="p-2 rounded-lg bg-background border border-border">
                  <span className="text-[10px] text-muted-foreground block">Price Estimate</span>
                  <span className="font-semibold text-emerald-700">
                    {selectedCall.extracted_slots.price_range_min && selectedCall.extracted_slots.price_range_max
                      ? `₹${selectedCall.extracted_slots.price_range_min} - ₹${selectedCall.extracted_slots.price_range_max}`
                      : "Standard rates"}
                  </span>
                </div>
              </div>
            </div>

            {/* Scrollable Conversation Bubbles */}
            <ScrollArea className="flex-1 p-5 overflow-y-auto">
              <CallTranscript call={selectedCall} />
            </ScrollArea>

            {/* Action Footer */}
            <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Extracted and verified by Pakka voice brain</span>
              </span>
              <Button size="sm" onClick={() => setSelectedCall(null)}>
                Done
              </Button>
            </div>
          </SheetContent>
        )}
      </Sheet>
    </div>
  );
}
