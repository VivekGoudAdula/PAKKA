import Link from "next/link";
import { cn } from "@/lib/utils";

interface PakkaLogoProps {
  className?: string;
  showTagline?: boolean;
  size?: "sm" | "md" | "lg";
  href?: string;
}

export function PakkaLogo({
  className,
  showTagline = false,
  size = "md",
  href = "/app",
}: PakkaLogoProps) {
  const stampSizes = {
    sm: "w-8 h-8 rounded-lg border-[2px]",
    md: "w-10 h-10 rounded-xl border-[2.5px]",
    lg: "w-12 h-12 rounded-2xl border-[3px]",
  };

  const textSizes = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
  };

  const stampInnerSizes = {
    sm: "text-[7.5px]",
    md: "text-[9.5px]",
    lg: "text-[11.5px]",
  };

  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-2.5 group transition-opacity hover:opacity-90 select-none",
        className
      )}
      aria-label="पक्का Home"
    >
      {/* Signature Yellow Pakka Stamp */}
      <div
        className={cn(
          "relative flex flex-col items-center justify-center rotate-[-7deg] transition-transform group-hover:rotate-0 group-hover:scale-105 shrink-0 select-none shadow-xs",
          "border-amber-500 text-amber-600 bg-amber-400/20 dark:border-amber-400 dark:text-amber-400 dark:bg-amber-400/10",
          stampSizes[size]
        )}
      >
        {/* Inner double-rule effect */}
        <span
          className="absolute inset-[1.5px] rounded-[inherit] border border-amber-500/40 dark:border-amber-400/40 pointer-events-none"
          aria-hidden="true"
        />
        <span className={cn("font-black tracking-tighter leading-none select-none", stampInnerSizes[size])}>
          PAKKA
        </span>
        <span className={cn("font-black leading-none -mt-0.5 select-none", stampInnerSizes[size])}>
          ✓
        </span>
      </div>

      {/* Brand Title: Hindi 'पक्का' beside the yellow stamp (English PAKKA is inside stamp) */}
      <div className="flex flex-col justify-center">
        <span
          className={cn(
            "font-black tracking-tight font-devanagari text-foreground leading-none",
            textSizes[size]
          )}
        >
          पक्का
        </span>
        {showTagline && (
          <span className="text-[11px] font-medium text-muted mt-1 leading-none">
            Picks up, books, chases money
          </span>
        )}
      </div>
    </Link>
  );
}
