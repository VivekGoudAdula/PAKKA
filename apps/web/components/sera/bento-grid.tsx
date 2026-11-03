import React from "react";
import { cn } from "@/lib/utils";

export function BentoGrid({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "grid w-full auto-rows-[16rem] grid-cols-1 md:grid-cols-3 gap-4",
        className
      )}
    >
      {children}
    </div>
  );
}

export function BentoCard({
  className,
  title,
  subtitle,
  children,
  badge,
  action,
}: {
  className?: string;
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
  badge?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-surface/90 p-5 shadow-xs transition-all duration-300 hover:border-primary/50 hover:shadow-sm",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2 z-10">
        <div>
          <h3 className="text-base font-bold text-ink">{title}</h3>
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {badge}
      </div>

      <div className="my-auto z-10">{children}</div>

      {action && <div className="mt-2 z-10">{action}</div>}

      {/* Subtle light glow on hover */}
      <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 bg-radial from-primary/5 to-transparent" />
    </div>
  );
}
