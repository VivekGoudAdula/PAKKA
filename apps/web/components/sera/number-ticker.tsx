/**
 * Sera UI — Number Ticker
 * Re-themed for Pakka light design tokens.
 *
 * Original: https://seraui.com/docs/components/number-ticker
 * Modification: replaced hard-coded dark colors with CSS token variables.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, useMotionValue, useSpring } from "framer-motion";
import { cn } from "@/lib/utils";

interface NumberTickerProps {
  /** Target numeric value to animate towards. */
  value: number;
  /** Prefix shown before the number (e.g. "₹"). */
  prefix?: string;
  /** Suffix shown after the number (e.g. "+"). */
  suffix?: string;
  /** Number of decimal places. @default 0 */
  decimalPlaces?: number;
  /** Additional class names. */
  className?: string;
}

/**
 * Animates a number from 0 to `value` using a spring when the element
 * enters the viewport. Re-themed from Sera UI dark palette to Pakka light
 * tokens: text colour uses `var(--ink)` instead of hard-coded white.
 */
export function NumberTicker({
  value,
  prefix = "",
  suffix = "",
  decimalPlaces = 0,
  className,
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -40px 0px" });

  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, {
    damping: 60,
    stiffness: 300,
  });
  const [displayValue, setDisplayValue] = useState("0");

  useEffect(() => {
    if (inView) {
      motionValue.set(value);
    }
  }, [inView, motionValue, value]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest) => {
      setDisplayValue(latest.toFixed(decimalPlaces));
    });
    return unsubscribe;
  }, [springValue, decimalPlaces]);

  return (
    <span
      ref={ref}
      className={cn("tabular-nums text-ink", className)}
      aria-label={`${prefix}${value}${suffix}`}
    >
      {prefix}
      {displayValue}
      {suffix}
    </span>
  );
}

