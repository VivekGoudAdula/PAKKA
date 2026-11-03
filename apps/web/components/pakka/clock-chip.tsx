"use client";

import { useMemo } from "react";
import { Clock, FastForward, RotateCcw } from "lucide-react";
import { useClockStore } from "@/lib/stores/clock-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

/**
 * ClockChip displays the current simulated time and allows the user
 * to fast-forward (+1 hour, +1 day) or reset to baseline.
 */
export function ClockChip() {
  const { baseDate, hoursOffset, daysOffset, advanceHours, advanceDays, resetClock } =
    useClockStore();

  const simulatedTime = useMemo(() => {
    const d = new Date(baseDate.getTime());
    d.setHours(d.getHours() + hoursOffset);
    d.setDate(d.getDate() + daysOffset);
    return d;
  }, [baseDate, hoursOffset, daysOffset]);

  const formattedTime = useMemo(() => {
    return simulatedTime.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  }, [simulatedTime]);

  const formattedDate = useMemo(() => {
    return simulatedTime.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
    });
  }, [simulatedTime]);

  const isShifted = hoursOffset > 0 || daysOffset > 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
        <div className="flex items-center gap-1.5 text-xs font-medium text-ink">
          <Clock className="w-3.5 h-3.5 text-primary animate-pulse" />
          <span className="font-semibold text-primary">{formattedDate}</span>
          <span className="text-muted-foreground">{formattedTime}</span>
          {isShifted && (
            <span className="ml-1 rounded bg-primary/10 px-1 py-0.2 text-[10px] font-bold text-primary">
              +{daysOffset > 0 ? `${daysOffset}d ` : ""}{hoursOffset > 0 ? `${hoursOffset % 24}h` : ""}
            </span>
          )}
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex items-center justify-between text-xs">
          <span>Simulated Clock</span>
          {isShifted && (
            <span className="text-[10px] font-normal text-muted-foreground">Fast-forwarded</span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="flex items-center justify-between cursor-pointer"
          onClick={() => advanceHours(1)}
        >
          <span className="flex items-center gap-2">
            <FastForward className="w-4 h-4 text-primary" />
            <span>Fast-forward 1 hour</span>
          </span>
          <kbd className="text-[10px] text-muted-foreground">+1h</kbd>
        </DropdownMenuItem>
        <DropdownMenuItem
          className="flex items-center justify-between cursor-pointer"
          onClick={() => advanceDays(1)}
        >
          <span className="flex items-center gap-2">
            <FastForward className="w-4 h-4 text-primary" />
            <span>Fast-forward 1 day</span>
          </span>
          <kbd className="text-[10px] text-muted-foreground">+1d</kbd>
        </DropdownMenuItem>
        {isShifted && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="flex items-center gap-2 text-destructive cursor-pointer"
              onClick={resetClock}
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset to real time</span>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
