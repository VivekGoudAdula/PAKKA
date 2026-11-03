import Link from "next/link";
import { cn } from "@/lib/utils";

interface PakkaLogoProps {
  className?: string;
  showTagline?: boolean;
  size?: "sm" | "md" | "lg";
}

export function PakkaLogo({
  className,
  showTagline = false,
  size = "md",
}: PakkaLogoProps) {
  const sizeClasses = {
    sm: "text-lg",
    md: "text-xl",
    lg: "text-2xl",
  };

  return (
    <Link
      href="/app"
      className={cn("inline-flex items-center gap-2 group transition-opacity hover:opacity-90", className)}
      aria-label="Pakka Dashboard Home"
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-fg font-black text-base shadow-xs transition-transform group-hover:scale-105">
        प
      </div>
      <div className="flex flex-col">
        <span
          className={cn(
            "font-black tracking-tight font-display text-ink flex items-center gap-1",
            sizeClasses[size]
          )}
        >
          Pakka
          <span className="text-primary text-xs font-bold uppercase tracking-wider bg-primary/10 px-1.5 py-0.5 rounded-md ml-0.5">
            पक्का
          </span>
        </span>
        {showTagline && (
          <span className="text-[11px] font-medium text-muted -mt-0.5">
            Picks up, books, chases money
          </span>
        )}
      </div>
    </Link>
  );
}
