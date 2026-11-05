"use client";

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  ChevronRight,
  Eye,
  EyeOff,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DEMO_BEATS, useDemoDirectorStore } from "@/lib/stores/demo-director-store";
import { cn } from "@/lib/utils";

interface DemoDirectorProps {
  onResetData?: () => void;
  className?: string;
}

export function DemoDirector({ onResetData, className }: DemoDirectorProps) {
  const router = useRouter();
  const {
    currentBeat,
    isPlaying,
    recordingMode,
    setBeat,
    nextBeat,
    togglePlay,
    toggleRecordingMode,
    resetDemo,
  } = useDemoDirectorStore();

  // Keyboard shortcuts: Space = play/pause, R = restart
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "KeyR" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        resetDemo();
        toast.info("Demo restarted from Beat 1");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePlay, resetDemo]);

  // Handle Beat Selection
  const handleSelectBeat = useCallback(
    (beatId: number) => {
      setBeat(beatId);
      const targetBeat = DEMO_BEATS.find((b) => b.id === beatId);
      if (targetBeat) {
        toast.success(`Jumping to Beat ${beatId}: ${targetBeat.name}`);
        router.push(targetBeat.route);
      }
    },
    [setBeat, router]
  );

  const handleReset = () => {
    resetDemo();
    if (onResetData) {
      onResetData();
    }
    toast.success("Demo state reset to initial seed values");
  };

  return (
    <aside
      aria-label="Demo Director Control Bar"
      className={cn(
        "fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-4xl",
        "rounded-2xl border border-border/80 bg-card/95 p-3 sm:p-4 shadow-2xl backdrop-blur-md",
        "transition-all duration-200",
        className
      )}
    >
      <div className="flex flex-col gap-3">
        {/* Top Header Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="font-display text-xs font-bold uppercase tracking-wider text-ink sm:text-sm">
              Demo Director
            </span>
            <Badge
              variant="outline"
              className="border-amber-500/30 bg-amber-500/10 text-amber-800 text-[11px] font-medium"
            >
              Scripted demo, not a live call
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            {/* Recording mode toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleRecordingMode}
              className={cn(
                "h-7 gap-1.5 px-2.5 text-xs font-medium",
                recordingMode
                  ? "bg-primary/10 text-primary hover:bg-primary/20"
                  : "text-muted hover:text-ink"
              )}
              title="Hide debug chips and latencies for clean 1920x1080 video recording"
            >
              {recordingMode ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              <span>{recordingMode ? "Recording Mode ON" : "Recording Mode"}</span>
            </Button>

            {/* Reset Action */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="h-7 gap-1.5 px-2 text-xs text-muted hover:text-ink"
              title="Reset demo data (Hotkey: R)"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Reset</span>
            </Button>
          </div>
        </div>

        {/* Middle Beat Timeline Stepper */}
        <div className="grid grid-cols-5 gap-1.5 sm:gap-2">
          {DEMO_BEATS.map((beat) => {
            const isActive = currentBeat === beat.id;
            const isCompleted = currentBeat > beat.id;

            return (
              <button
                key={beat.id}
                type="button"
                onClick={() => handleSelectBeat(beat.id)}
                className={cn(
                  "flex flex-col items-start rounded-lg border p-1.5 sm:p-2 text-left transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  isActive
                    ? "border-primary bg-primary/10 shadow-sm"
                    : isCompleted
                    ? "border-success/30 bg-success/5 hover:border-success/50"
                    : "border-border/60 bg-muted/20 opacity-70 hover:opacity-100"
                )}
              >
                <div className="flex w-full items-center justify-between">
                  <span
                    className={cn(
                      "font-mono text-[10px] font-bold",
                      isActive
                        ? "text-primary"
                        : isCompleted
                        ? "text-success"
                        : "text-muted"
                    )}
                  >
                    BEAT 0{beat.id}
                  </span>
                  {isCompleted && (
                    <CheckCircle2 className="h-3 w-3 text-success shrink-0" />
                  )}
                </div>
                <span className="mt-0.5 truncate text-[11px] font-semibold text-ink sm:text-xs">
                  {beat.shortLabel}
                </span>
              </button>
            );
          })}
        </div>

        {/* Bottom Playback Control Bar */}
        <div className="flex items-center justify-between pt-1 text-xs text-muted">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={togglePlay}
              className={cn(
                "h-8 gap-2 px-4 font-semibold text-white shadow-sm",
                isPlaying
                  ? "bg-amber-600 hover:bg-amber-700"
                  : "bg-primary hover:bg-primary/90"
              )}
            >
              {isPlaying ? (
                <>
                  <Pause className="h-4 w-4 fill-white" />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  <span>Play Demo</span>
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={nextBeat}
              disabled={currentBeat >= 5}
              className="h-8 gap-1.5 px-3 text-xs"
              title="Advance to next beat"
            >
              <span>Next Beat</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>

          <div className="hidden items-center gap-3 sm:flex text-[11px] font-mono text-muted">
            <span>
              <kbd className="rounded border border-border bg-muted/40 px-1 py-0.5">Space</kbd> Play/Pause
            </span>
            <span>
              <kbd className="rounded border border-border bg-muted/40 px-1 py-0.5">R</kbd> Restart
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
