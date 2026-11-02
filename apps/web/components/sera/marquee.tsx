/**
 * Sera UI — Marquee
 * Re-themed for Pakka light design tokens.
 *
 * Original: https://seraui.com/docs/components/marquee
 * Modification: removed dark background, used CSS token variables for
 * gradient fade edges and text color.
 */
"use client";

import { cn } from "@/lib/utils";

interface MarqueeProps {
  /** Array of strings or nodes to display. */
  items: React.ReactNode[];
  /** Direction of scroll. @default "left" */
  direction?: "left" | "right";
  /** Speed in seconds per full loop. @default 30 */
  duration?: number;
  /** Whether to pause on hover. @default true */
  pauseOnHover?: boolean;
  /** Additional class names on the wrapper. */
  className?: string;
}

/**
 * A continuously scrolling marquee strip.
 * Items are duplicated to create a seamless loop.
 *
 * Re-themed from Sera UI: gradient edges use `var(--background)` so they
 * blend naturally on our warm paper background.
 */
export function Marquee({
  items,
  direction = "left",
  duration = 30,
  pauseOnHover = true,
  className,
}: MarqueeProps) {
  return (
    <div
      className={cn(
        "relative flex overflow-hidden [--duration:30s]",
        className,
      )}
      style={{ "--duration": `${duration}s` } as React.CSSProperties}
      role="marquee"
      aria-label="Scrolling content"
    >
      {/* Fade edges */}
      <div
        className="pointer-events-none absolute left-0 top-0 z-10 h-full w-16"
        style={{
          background: `linear-gradient(to right, var(--background), transparent)`,
        }}
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute right-0 top-0 z-10 h-full w-16"
        style={{
          background: `linear-gradient(to left, var(--background), transparent)`,
        }}
        aria-hidden="true"
      />

      {/* Track — duplicated for seamless loop */}
      <div
        style={{
          animation: `var(--animate-marquee-${direction})`,
          animationPlayState: "running",
        }}
        onMouseEnter={pauseOnHover ? (e) => { (e.currentTarget as HTMLElement).style.animationPlayState = "paused"; } : undefined}
        onMouseLeave={pauseOnHover ? (e) => { (e.currentTarget as HTMLElement).style.animationPlayState = "running"; } : undefined}
        className="flex min-w-full shrink-0 gap-4 py-2"
        aria-hidden="true"
      >
        {items.map((item, i) => (
          <div key={i} className="shrink-0">
            {item}
          </div>
        ))}
      </div>
      {/* Duplicate for seamless loop */}
      <div
        style={{
          animation: `var(--animate-marquee-${direction})`,
          animationPlayState: "running",
        }}
        onMouseEnter={pauseOnHover ? (e) => { (e.currentTarget as HTMLElement).style.animationPlayState = "paused"; } : undefined}
        onMouseLeave={pauseOnHover ? (e) => { (e.currentTarget as HTMLElement).style.animationPlayState = "running"; } : undefined}
        className="flex min-w-full shrink-0 gap-4 py-2"
        aria-hidden="true"
      >
        {items.map((item, i) => (
          <div key={`dup-${i}`} className="shrink-0">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
