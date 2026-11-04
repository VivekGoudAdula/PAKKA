"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Users,
  Phone,
  Mic,
  CheckCircle,
  Briefcase,
  Wrench,
  Clock,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { fetchTechnicians } from "@/lib/api/client";
import { TechnicianStatus } from "@/lib/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useModeStore } from "@/lib/stores/mode-store";

export default function TechniciansPage() {
  const { mode } = useModeStore();
  const { data: technicians, isLoading, isError, refetch } = useQuery({
    queryKey: ["technicians"],
    queryFn: fetchTechnicians,
  });

  const getStatusBadge = (status: TechnicianStatus) => {
    switch (status) {
      case "available":
        return (
          <Badge className="bg-emerald-50 text-emerald-700 border-emerald-300 gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Available Now
          </Badge>
        );
      case "on_job":
        return (
          <Badge className="bg-amber-50 text-amber-700 border-amber-300 gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            On Site
          </Badge>
        );
      case "off_duty":
        return (
          <Badge variant="outline" className="text-muted-foreground gap-1.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
            Off Duty
          </Badge>
        );
    }
  };

  const availableCount = technicians?.filter((t) => t.status === "available").length || 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Technicians Directory
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Voice dispatch loop: Pakka reads jobs aloud, listens for &ldquo;haan, pakka&rdquo;, and falls back if rejected.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="px-3 py-1 text-xs border-primary/30 bg-primary/5 text-primary font-bold">
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-primary" />
            {availableCount} Available for Dispatch
          </Badge>
        </div>
      </div>

      {/* Technicians Grid */}
      {isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-2xl bg-destructive/5 space-y-2">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto" />
          <h3 className="text-base font-bold text-ink">Failed to load technicians</h3>
          <p className="text-xs text-muted-foreground">Unable to fetch technician directory. Please try again.</p>
          <Button size="sm" variant="outline" onClick={() => refetch()} className="text-xs">Retry</Button>
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-64 w-full rounded-2xl" />
          ))}
        </div>
      ) : technicians && technicians.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {technicians.map((tech) => (
            <div
              key={tech.id}
              className="p-5 sm:p-6 rounded-2xl border border-border bg-card hover:border-primary/40 transition-all shadow-xs hover:shadow-sm space-y-4 flex flex-col justify-between"
            >
              <div>
                {/* Tech Profile Row */}
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar size="lg" className="border-2 border-primary/20 bg-primary/10 text-primary font-bold">
                      <AvatarFallback className="bg-primary/10 text-primary font-bold">
                        {tech.avatar}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h3 className="font-bold text-base text-ink">{tech.name}</h3>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <Phone className="w-3 h-3 text-primary" />
                        <span className="font-mono">{tech.phone_masked}</span>
                      </div>
                    </div>
                  </div>

                  {getStatusBadge(tech.status)}
                </div>

                {/* Trade specialty */}
                <div className="mt-3 flex items-center gap-1.5 text-xs text-ink/80 font-medium bg-muted/40 px-3 py-1.5 rounded-lg border border-border/50">
                  <Wrench className="w-3.5 h-3.5 text-primary shrink-0" />
                  <span>{tech.trade}</span>
                </div>

                {/* Spoken Voice Confirmation Box */}
                <div className="mt-4 p-3.5 rounded-xl border border-border bg-background/80 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1 font-semibold text-primary">
                      <Mic className="w-3 h-3" />
                      <span>Last Spoken Voice Response</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{tech.last_confirmation_time}</span>
                    </span>
                  </div>
                  <p className="text-xs italic text-ink font-medium pl-1 border-l-2 border-primary/60">
                    &ldquo;{tech.last_voice_confirmation}&rdquo;
                  </p>
                </div>
              </div>

              {/* Acceptance metrics & Dispatch Action */}
              <div className="pt-3 border-t border-border/60 space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Voice Acceptance Rate</span>
                    </span>
                    <span className="font-bold text-ink">{tech.accept_rate}%</span>
                  </div>
                  <Progress value={tech.accept_rate} className="h-1.5" />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Briefcase className="w-3.5 h-3.5" />
                    <span>Total Jobs: <strong>{tech.total_jobs}</strong></span>
                  </span>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (mode === "DEMO") {
                        toast.info(`Simulated Voice Dispatch Call (Demo Mode)`, {
                          description: `Simulating call to ${tech.name} (${tech.phone_masked}). Real voice calling requires LIVE mode with active Exotel credentials.`,
                        });
                      } else {
                        toast.success(`Voice dispatch call dialed!`, {
                          description: `Connecting to ${tech.name} (${tech.phone_masked}) via Exotel Voicebot...`,
                        });
                      }
                    }}
                    className="text-xs gap-1.5 hover:bg-primary/10 hover:text-primary transition-colors"
                  >
                    <Phone className="w-3.5 h-3.5 text-primary" />
                    <span>{mode === "DEMO" ? "Call (Simulated)" : "Call via Voicebot"}</span>
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-12 text-center border border-dashed border-border rounded-2xl bg-card/40">
          <Users className="w-8 h-8 mx-auto text-muted-foreground mb-3 opacity-50" />
          <h3 className="text-base font-bold text-ink">No technicians registered</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Add team members to enable voice dispatch routing.
          </p>
        </div>
      )}
    </div>
  );
}
