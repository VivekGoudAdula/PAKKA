import { Call } from "@/lib/types";
import { ShieldCheck, User, Bot } from "lucide-react";

interface CallTranscriptProps {
  call: Call;
}

/**
 * CallTranscript renders conversation turns using daisyUI's prefixed chat components.
 * Per project rules: strictly prefix `daisy-` and do not mix with other primitives in this component.
 */
export function CallTranscript({ call }: CallTranscriptProps) {
  return (
    <div className="space-y-4 py-2">
      {call.transcript.map((msg, idx) => {
        const isBot = msg.role === "bot";
        const isFirstBotMessage = isBot && (msg.is_disclosure || idx === 0);

        return (
          <div
            key={msg.id || idx}
            className={`daisy-chat ${isBot ? "daisy-chat-start" : "daisy-chat-end"}`}
          >
            <div className="daisy-chat-image daisy-avatar">
              <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted text-ink border border-border">
                {isBot ? (
                  <Bot className="w-4 h-4 text-primary" />
                ) : (
                  <User className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </div>

            <div className="daisy-chat-header text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
              <span>{isBot ? "Pakka Assistant" : (call.customer_name || "Caller")}</span>
              <time className="text-[10px] opacity-70">{msg.timestamp}</time>
            </div>

            <div
              className={`daisy-chat-bubble text-sm leading-relaxed ${
                isBot
                  ? "bg-muted text-ink border border-border/80"
                  : "bg-primary text-white font-medium"
              }`}
            >
              {msg.text}
            </div>

            {/* AI digital assistant disclosure notification on first message */}
            {isFirstBotMessage && (
              <div className="daisy-chat-footer text-[10px] text-emerald-700 font-medium mt-1 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-emerald-600" />
                <span>Mandatory AI identity disclosure stated</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
