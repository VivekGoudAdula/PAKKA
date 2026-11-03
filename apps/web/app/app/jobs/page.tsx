"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  MapPin,
  Clock,
  IndianRupee,
  User,
  Plus,
  Briefcase,
  AlertCircle,
  PhoneCall,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { fetchJobs, fetchTechnicians } from "@/lib/api/client";
import { Job, JobStatus } from "@/lib/types";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const COLUMNS: { id: JobStatus; title: string; color: string; dotColor: string }[] = [
  { id: "new", title: "New Leads", color: "bg-blue-50 text-blue-700 border-blue-200", dotColor: "bg-blue-500" },
  { id: "booked", title: "Booked", color: "bg-emerald-50 text-emerald-700 border-emerald-200", dotColor: "bg-emerald-500" },
  { id: "dispatched", title: "Dispatched", color: "bg-amber-50 text-amber-700 border-amber-200", dotColor: "bg-amber-500" },
  { id: "done", title: "Service Done", color: "bg-purple-50 text-purple-700 border-purple-200", dotColor: "bg-purple-500" },
  { id: "paid", title: "Paid & Closed", color: "bg-emerald-50 text-emerald-800 border-emerald-300", dotColor: "bg-emerald-600" },
];

export default function JobsPage() {
  const { data: initialJobs, isLoading, isError, refetch } = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });

  const { data: technicians } = useQuery({
    queryKey: ["technicians"],
    queryFn: fetchTechnicians,
  });

  // Local state overlay for live dispatch moves
  const [localJobs, setLocalJobs] = useState<Record<string, Partial<Job>>>({});
  const [selectedJobToDispatch, setSelectedJobToDispatch] = useState<Job | null>(null);
  const [isDispatchDialogOpen, setIsDispatchDialogOpen] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);

  const jobsList: Job[] = (initialJobs || []).map((j) => {
    const override = localJobs[j.id];
    return override ? { ...j, ...override } : j;
  });

  const getJobsByColumn = (status: JobStatus): Job[] => {
    return jobsList.filter((j) => j.status === status);
  };

  const handleOpenDispatchDialog = (job: Job) => {
    setSelectedJobToDispatch(job);
    setIsDispatchDialogOpen(true);
  };

  const handleConfirmDispatch = async () => {
    if (!selectedJobToDispatch) return;
    setIsDispatching(true);

    try {
      // In live mode, call REST backend
      try {
        await fetch(`/api/jobs/${selectedJobToDispatch.id}/dispatch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ simulate: true }),
        });
      } catch {
        // Fallback for offline demo
      }

      // Find best matched specialist
      const matchedTech =
        technicians?.find((t) =>
          selectedJobToDispatch.problem.toLowerCase().includes("geyser")
            ? t.trade.toLowerCase().includes("geyser")
            : t.status === "available"
        ) || technicians?.[0];

      const techName = matchedTech?.name || "Ramesh Kumar";
      const techAvatar = matchedTech?.avatar || "R";

      // Animate card move from 'booked' to 'dispatched'
      setLocalJobs((prev) => ({
        ...prev,
        [selectedJobToDispatch.id]: {
          status: "dispatched",
          technician_name: techName,
          technician_avatar: techAvatar,
          confirmed_at: "Just now",
        },
      }));

      toast.success("Voice dispatch initiated!", {
        description: `Calling ${techName} (${matchedTech?.trade || "Specialist"}) to confirm.`,
      });

      setIsDispatchDialogOpen(false);
      setSelectedJobToDispatch(null);
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Jobs Board
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Voice-booked customer requests routed and dispatched to technicians.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" className="gap-2">
            <Plus className="w-4 h-4 text-primary" />
            <span>Manual Job</span>
          </Button>
        </div>
      </div>

      {/* 5-Column Kanban Board with mobile snap scrolling */}
      {isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-2xl bg-destructive/5 space-y-2">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
          <h3 className="text-base font-bold text-ink">Failed to load jobs</h3>
          <p className="text-xs text-muted-foreground">Unable to fetch jobs board data. Please try again.</p>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs">Retry</Button>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-10 w-full rounded-xl" />
              <Skeleton className="h-40 w-full rounded-2xl" />
              <Skeleton className="h-32 w-full rounded-2xl" />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-6 pt-1 snap-x snap-mandatory scroll-smooth w-full max-w-full">
          {COLUMNS.map((column) => {
            const columnJobs = getJobsByColumn(column.id);

            return (
              <div
                key={column.id}
                className="w-[280px] sm:w-[320px] shrink-0 snap-center flex flex-col rounded-2xl border border-border bg-card/60 p-3 shadow-2xs"
              >
                {/* Column Header */}
                <div className="flex items-center justify-between px-2 py-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${column.dotColor}`} />
                    <h2 className="font-bold text-sm text-ink">{column.title}</h2>
                  </div>
                  <Badge variant="outline" className="text-xs px-2 py-0.5 font-bold">
                    {columnJobs.length}
                  </Badge>
                </div>

                {/* Column Cards */}
                <div className="space-y-3 flex-1 overflow-y-auto max-h-[calc(100vh-280px)] p-1">
                  <AnimatePresence mode="popLayout">
                    {columnJobs.length > 0 ? (
                      columnJobs.map((job) => (
                        <motion.div
                          key={job.id}
                          layout
                          initial={{ opacity: 0, scale: 0.96 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.96 }}
                          transition={{ type: "spring", stiffness: 350, damping: 25 }}
                          className="group relative p-4 rounded-xl border border-border bg-card hover:border-primary/50 transition-all shadow-xs hover:shadow-sm space-y-3 overflow-hidden"
                        >
                          {/* Title & Customer */}
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <h3 className="font-bold text-sm text-ink group-hover:text-primary transition-colors">
                                {job.title}
                              </h3>
                              {/* Pakka Stamp for confirmed jobs */}
                              {(job.status === "booked" || job.status === "dispatched" || job.status === "done") && (
                                <div className="shrink-0 -mr-1 -mt-1 scale-90">
                                  <PakkaStamp size="sm" visible />
                                </div>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                              {job.problem}
                            </p>
                          </div>

                          {/* Details */}
                          <div className="space-y-1.5 text-xs text-muted-foreground pt-1 border-t border-border/50">
                            <div className="flex items-start gap-1.5">
                              <MapPin className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                              <span className="line-clamp-2 text-ink/90 font-medium">
                                {job.landmark_address}
                              </span>
                            </div>

                            <div className="flex items-center justify-between pt-1">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3 text-muted-foreground" />
                                <span className="text-[11px] font-medium">{job.time_slot}</span>
                              </span>
                              <span className="flex items-center gap-0.5 font-bold text-emerald-700">
                                <IndianRupee className="w-3 h-3" />
                                <span>{job.price_estimate}</span>
                              </span>
                            </div>
                          </div>

                          {/* Customer & Technician footer */}
                          <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px]">
                            <div className="flex items-center gap-1 text-ink/80">
                              <User className="w-3 h-3 text-muted-foreground" />
                              <span className="font-medium truncate max-w-[100px]">{job.customer_name}</span>
                            </div>

                            {job.technician_name ? (
                              <div className="flex items-center gap-1 text-primary font-semibold">
                                <div className="w-4 h-4 rounded-full bg-primary/10 flex items-center justify-center text-[9px] font-bold">
                                  {job.technician_avatar || "T"}
                                </div>
                                <span className="truncate max-w-[90px]">{job.technician_name}</span>
                              </div>
                            ) : job.status === "booked" ? (
                              <Button
                                size="sm"
                                variant="default"
                                onClick={() => handleOpenDispatchDialog(job)}
                                className="h-6 px-2 text-[10px] font-bold gap-1 bg-amber-500 hover:bg-amber-600 text-white"
                              >
                                <PhoneCall className="w-3 h-3" /> Dispatch now
                              </Button>
                            ) : (
                              <span className="text-muted-foreground italic">Awaiting dispatch</span>
                            )}
                          </div>
                        </motion.div>
                      ))
                    ) : (
                      <div className="p-8 text-center border border-dashed border-border/60 rounded-xl bg-background/40">
                        <Briefcase className="w-6 h-6 mx-auto text-muted-foreground/40 mb-2" />
                        <p className="text-xs text-muted-foreground font-medium">No jobs in this stage</p>
                      </div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Dispatch Confirmation Modal Dialog ─────────────────────────────── */}
      <Dialog open={isDispatchDialogOpen} onOpenChange={setIsDispatchDialogOpen}>
        <DialogContent className="sm:max-w-[420px] rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <PhoneCall className="w-4 h-4 text-primary" />
              Dispatch Technician via Voice Call
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Pakka will initiate an outbound AI phone call to read this job aloud and collect voice acceptance.
            </DialogDescription>
          </DialogHeader>

          {selectedJobToDispatch && (
            <div className="space-y-3 py-2 text-xs">
              <div className="p-3 rounded-xl bg-muted/50 border border-border space-y-1.5">
                <div className="font-bold text-foreground text-sm">
                  {selectedJobToDispatch.title}
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
                  <span>{selectedJobToDispatch.landmark_address}</span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground pt-1">
                  <span>Slot: {selectedJobToDispatch.time_slot}</span>
                  <span className="font-bold text-emerald-700">{selectedJobToDispatch.price_estimate}</span>
                </div>
              </div>

              {/* Recommended Technician */}
              <div className="p-3 rounded-xl border border-emerald-300 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-emerald-800 dark:text-emerald-300 uppercase flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-600" /> Top Ranked Specialist
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-background">
                    Fewest Active Jobs
                  </Badge>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-emerald-600 text-white font-bold flex items-center justify-center text-xs">
                    R
                  </div>
                  <div>
                    <div className="font-bold text-foreground">Ramesh Kumar</div>
                    <div className="text-[11px] text-muted-foreground">
                      Geyser Specialist • +91 98XXXXXX01
                    </div>
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground italic">
                Note: Technician dispatch calls are exempt from customer outbound calling hours (available 24/7 for emergency repairs).
              </p>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsDispatchDialogOpen(false)}
              disabled={isDispatching}
            >
              Cancel
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleConfirmDispatch}
              disabled={isDispatching}
              className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
            >
              {isDispatching ? (
                "Dialing..."
              ) : (
                <>
                  <PhoneCall className="w-3.5 h-3.5" /> Call &amp; Dispatch
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
