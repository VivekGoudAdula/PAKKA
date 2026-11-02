"use client";

import { cn } from "@/lib/utils";

interface TranscriptBubbleProps {
  /** The speaker: caller (customer) or assistant (Pakka AI). */
  role: "caller" | "assistant";
  /** Transcript text. */
  text: string;
  /** Optional timestamp string (e.g. "2:14 PM"). */
  timestamp?: string;
  /** Whether this is a partial/streaming transcript. */
  isPartial?: boolean;
  /** Additional class names on the container. */
  className?: string;
}

/**
 * Live transcript chat bubble.
 *
 * Uses daisyUI `chat` classes with a `daisy-` prefix to avoid collisions.
 * Colours are overridden with Pakka CSS token variables — no daisyUI theme
 * variables are used.
 *
 * @note daisyUI must be configured with `prefix: "daisy-"` and
 *       `themes: false` and `base: false` in tailwind config / postcss.
 */
export function TranscriptBubble({
  role,
  text,
  timestamp,
  isPartial = false,
  className,
}: TranscriptBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={cn(
        "daisy-chat",
        isAssistant ? "daisy-chat-start" : "daisy-chat-end",
        className,
      )}
    >
      {/* Avatar indicator */}
      <div
        className="daisy-chat-image"
        aria-hidden="true"
      >
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
            isAssistant
              ? "bg-primary text-primary-fg"
              : "bg-surface-2 text-muted border border-border",
          )}
        >
          {isAssistant ? "P" : "C"}
        </div>
      </div>

      {/* Header */}
      <div className="daisy-chat-header mb-1 text-xs text-muted">
        {isAssistant ? "Pakka AI" : "Caller"}
        {timestamp && (
          <time className="ml-2 text-muted opacity-60">{timestamp}</time>
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "daisy-chat-bubble font-mono text-sm leading-relaxed max-w-[75%]",
          isAssistant
            ? "bg-primary/10 text-ink border border-primary/20"
            : "bg-surface border border-border text-ink",
          isPartial && "opacity-70 italic",
        )}
        aria-live={isPartial ? "polite" : undefined}
        aria-label={`${isAssistant ? "Assistant" : "Caller"}: ${text}`}
      >
        {text}
        {isPartial && (
          <span className="ml-1 inline-block animate-pulse text-primary" aria-hidden="true">
            ▌
          </span>
        )}
      </div>
    </div>
  );
}

