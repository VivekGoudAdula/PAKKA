import { cn } from "@/lib/utils";

interface AnimatedBadgeProps {
  label: string;
  variant?: "success" | "primary" | "warning" | "danger" | "muted";
  className?: string;
  pulse?: boolean;
}

export function AnimatedBadge({
  label,
  variant = "primary",
  className,
  pulse = true,
}: AnimatedBadgeProps) {
  const colorMap = {
    primary: {
      bg: "bg-primary/10 text-primary-fg border-primary/30",
      dot: "bg-primary",
      pulse: "bg-primary/50",
    },
    success: {
      bg: "bg-success/10 text-success border-success/30",
      dot: "bg-success",
      pulse: "bg-success/50",
    },
    warning: {
      bg: "bg-warning/10 text-warning border-warning/30",
      dot: "bg-warning",
      pulse: "bg-warning/50",
    },
    danger: {
      bg: "bg-danger/10 text-danger border-danger/30",
      dot: "bg-danger",
      pulse: "bg-danger/50",
    },
    muted: {
      bg: "bg-muted/10 text-muted border-muted/30",
      dot: "bg-muted",
      pulse: "bg-muted/50",
    },
  };

  const current = colorMap[variant];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide",
        current.bg,
        className
      )}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              current.pulse
            )}
          />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", current.dot)} />
      </span>
      {label}
    </span>
  );
}
