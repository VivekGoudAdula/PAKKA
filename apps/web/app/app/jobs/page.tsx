"use client";

import { useQuery } from "@tanstack/react-query";
import {
  MapPin,
  Clock,
  IndianRupee,
  User,
  Plus,
  Briefcase,
} from "lucide-react";
import { fetchJobs } from "@/lib/api/client";
import { Job, JobStatus } from "@/lib/types";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

const COLUMNS: { id: JobStatus; title: string; color: string; dotColor: string }[] = [
  { id: "new", title: "New Leads", color: "bg-blue-50 text-blue-700 border-blue-200", dotColor: "bg-blue-500" },
  { id: "booked", title: "Booked", color: "bg-emerald-50 text-emerald-700 border-emerald-200", dotColor: "bg-emerald-500" },
  { id: "dispatched", title: "Dispatched", color: "bg-amber-50 text-amber-700 border-amber-200", dotColor: "bg-amber-500" },
  { id: "done", title: "Service Done", color: "bg-purple-50 text-purple-700 border-purple-200", dotColor: "bg-purple-500" },
  { id: "paid", title: "Paid & Closed", color: "bg-emerald-50 text-emerald-800 border-emerald-300", dotColor: "bg-emerald-600" },
];

export default function JobsPage() {
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  });

  const getJobsByColumn = (status: JobStatus): Job[] => {
    if (!jobs) return [];
    return jobs.filter((j) => j.status === status);
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
      {isLoading ? (
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
                  {columnJobs.length > 0 ? (
                    columnJobs.map((job) => (
                      <div
                        key={job.id}
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
                          ) : (
                            <span className="text-muted-foreground italic">Awaiting dispatch</span>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center border border-dashed border-border/60 rounded-xl bg-background/40">
                      <Briefcase className="w-6 h-6 mx-auto text-muted-foreground/40 mb-2" />
                      <p className="text-xs text-muted-foreground font-medium">No jobs in this stage</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
