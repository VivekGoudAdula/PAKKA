"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

/** Variant controls colour and size of the stamp. */
type StampVariant = "success" | "primary";
type StampSize = "sm" | "md" | "lg";

interface PakkaStampProps {
  /** @default "success" */
  variant?: StampVariant;
  /** @default "md" */
  size?: StampSize;
  /** Additional class names on the outer wrapper. */
  className?: string;
  /** Whether the stamp is visible. Drives the spring-in animation. */
  visible?: boolean;
}

const sizeMap: Record<StampSize, { outer: string; text: string; sub: string }> = {
  sm: { outer: "w-20 h-20 rounded-xl border-[3px]", text: "text-base font-black", sub: "text-[9px]" },
  md: { outer: "w-32 h-32 rounded-2xl border-[4px]", text: "text-2xl font-black", sub: "text-[11px]" },
  lg: { outer: "w-48 h-48 rounded-3xl border-[6px]", text: "text-4xl font-black", sub: "text-sm" },
};

const colorMap: Record<StampVariant, string> = {
  success: "border-success text-success",
  primary: "border-primary text-primary",
};

/**
 * The signature PAKKA ✓ stamp component.
 *
 * Uses a Framer Motion spring to scale in from 0 → 1 with a slight
 * rotation wobble. Respects `prefers-reduced-motion`.
 *
 * @example
 * <PakkaStamp visible={isBooked} variant="success" size="lg" />
 */
export function PakkaStamp({
  variant = "success",
  size = "md",
  className,
  visible = true,
}: PakkaStampProps) {
  const prefersReduced = useReducedMotion();
  const { outer, text, sub } = sizeMap[size];

  return (
    <motion.div
      role="img"
      aria-label="Pakka — confirmed"
      className={cn(
        "inline-flex flex-col items-center justify-center select-none",
        "relative rotate-[-8deg]",
        outer,
        colorMap[variant],
        className,
      )}
      initial={prefersReduced ? { opacity: 0, scale: 1 } : { opacity: 0, scale: 0 }}
      animate={
        visible
          ? prefersReduced
            ? { opacity: 1, scale: 1 }
            : { opacity: 1, scale: 1, rotate: -8 }
          : { opacity: 0, scale: 0 }
      }
      transition={
        prefersReduced
          ? { duration: 0.15 }
          : {
              type: "spring",
              stiffness: 400,
              damping: 20,
              mass: 0.8,
            }
      }
    >
      {/* Inner double-rule effect via a slightly inset box */}
      <span
        className={cn(
          "absolute inset-[4px] rounded-[inherit]",
          "border-2 opacity-40",
          variant === "success" ? "border-success" : "border-primary",
        )}
        aria-hidden="true"
      />

      {/* Stamp text */}
      <span className={cn("leading-none tracking-tight z-10", text)}>
        PAKKA
      </span>
      <span className={cn("leading-none z-10", text)}>✓</span>
      <span className={cn("mt-1 font-devanagari opacity-70 z-10", sub)}>
        पक्का
      </span>
    </motion.div>
  );
}

