"use client";

import { cn } from "@/lib/utils";

export interface TimelineItem {
  id: string;
  time: string;
  title: string;
  description?: string;
  badge?: string;
  type?: "call" | "booking" | "dispatch" | "payment" | "reminder";
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

export function Timeline({ items, className }: TimelineProps) {
  return (
    <div className={cn("relative pl-6 space-y-6", className)}>
      {/* Continuous vertical line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-[2px] bg-border/80" />

      {items.map((item) => {
        const isSuccess = item.type === "booking" || item.type === "payment";
        const isPrimary = item.type === "call" || item.type === "dispatch";

        return (
          <div key={item.id} className="relative group">
            {/* Dot indicator */}
            <div
              className={cn(
                "absolute -left-6 top-1 h-[14px] w-[14px] rounded-full border-2 border-surface transition-transform duration-200 group-hover:scale-125",
                isSuccess
                  ? "bg-success"
                  : isPrimary
                  ? "bg-primary"
                  : "bg-muted-foreground/60"
              )}
            />

            <div className="rounded-xl border border-border/80 bg-surface/80 p-3.5 shadow-xs transition-colors hover:border-primary/40 hover:bg-surface">
              <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1">
                <span className="text-xs font-medium text-muted">{item.time}</span>
                {item.badge && (
                  <span className="inline-flex items-center rounded-md bg-secondary/80 px-2 py-0.5 text-[11px] font-semibold text-secondary-foreground">
                    {item.badge}
                  </span>
                )}
              </div>
              <h4 className="text-sm font-semibold text-ink">{item.title}</h4>
              {item.description && (
                <p className="mt-1 text-xs text-muted leading-relaxed">
                  {item.description}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
