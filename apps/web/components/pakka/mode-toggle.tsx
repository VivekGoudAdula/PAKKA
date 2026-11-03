"use client";

import { toast } from "sonner";
import { useModeStore } from "@/lib/stores/mode-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ModeToggle({ className }: { className?: string }) {
  const { mode, setMode } = useModeStore();

  const handleToggle = () => {
    const nextMode = mode === "DEMO" ? "LIVE" : "DEMO";
    setMode(nextMode);
    if (nextMode === "LIVE") {
      toast.info("Switched to LIVE mode", {
        description: "Listening for real Exotel telephony WebSocket events at ws://localhost:8000/ws/events.",
      });
    } else {
      toast.success("Switched to DEMO mode", {
        description: "Operating with seeded synthetic plumbing & geyser repair data.",
      });
    }
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border/80 bg-surface/90 p-1 shadow-xs",
        className
      )}
    >
      <Button
        variant={mode === "DEMO" ? "default" : "ghost"}
        size="sm"
        onClick={() => mode !== "DEMO" && handleToggle()}
        className={cn(
          "h-6 sm:h-7 rounded-full px-2 sm:px-3 text-[11px] sm:text-xs font-semibold transition-all",
          mode === "DEMO"
            ? "bg-primary text-primary-fg shadow-xs"
            : "text-muted hover:text-ink"
        )}
      >
        DEMO
      </Button>
      <Button
        variant={mode === "LIVE" ? "default" : "ghost"}
        size="sm"
        onClick={() => mode !== "LIVE" && handleToggle()}
        className={cn(
          "h-6 sm:h-7 rounded-full px-2 sm:px-3 text-[11px] sm:text-xs font-semibold transition-all",
          mode === "LIVE"
            ? "bg-success text-white shadow-xs"
            : "text-muted hover:text-ink"
        )}
      >
        LIVE
      </Button>
    </div>
  );
}
