/**
 * apps/web/lib/events.ts
 * Unified EventSource abstraction for realtime telephony & dispatch events.
 * Provides LiveWS (WebSocket to backend hub), DryRun, and DemoEventSource
 * (scripted ~40s booking + ~20s dispatch timeline with play/pause/restart).
 */

export type PakkaEvent =
  | {
      type: "call.started";
      payload: {
        call_id: string;
        stream_sid?: string;
        caller_number_masked: string;
        timestamp: number;
      };
    }
  | {
      type: "transcript";
      payload: {
        call_id: string;
        role: "caller" | "bot";
        text: string;
        language?: string;
        is_final?: boolean;
        is_disclosure?: boolean;
        timestamp: number;
      };
    }
  | {
      type: "bot.speaking";
      payload: {
        call_id: string;
        text: string;
        timestamp: number;
      };
    }
  | {
      type: "barge_in";
      payload: {
        call_id: string;
        timestamp: number;
      };
    }
  | {
      type: "slot.updated";
      payload: {
        call_id: string;
        field: "problem" | "landmark_address" | "time_slot" | "price_estimate";
        value: string;
      };
    }
  | {
      type: "fsm.state";
      payload: {
        call_id: string;
        state: "GREETING" | "PROBLEM" | "ADDRESS" | "SLOT" | "QUOTE" | "CONFIRM" | "BOOKED" | "HANDOFF";
      };
    }
  | {
      type: "job.booked";
      payload: {
        job_id: string;
        call_id: string;
        summary: string;
        problem: string;
        landmark_address: string;
        time_slot: string;
        price_estimate: string;
        price_min: number;
        price_max: number;
        customer_name?: string;
        customer_phone_masked?: string;
      };
    }
  | {
      type: "call.handoff";
      payload: {
        call_id: string;
        reason: string;
        urgent: boolean;
      };
    }
  | {
      type: "call.ended";
      payload: {
        call_id: string;
        duration_seconds?: number;
      };
    }
  | {
      type: "dispatch.started";
      payload: {
        job_id: string;
        call_id?: string;
        technician: {
          id: string;
          name: string;
          phone: string;
          specialty: string;
          avatar?: string;
        };
        attempt_number: number;
        timestamp?: number;
      };
    }
  | {
      type: "dispatch.ringing";
      payload: {
        job_id: string;
        technician: string;
        timestamp?: number;
      };
    }
  | {
      type: "dispatch.transcript";
      payload: {
        job_id: string;
        role: "technician" | "bot";
        text: string;
        is_disclosure?: boolean;
        timestamp?: number;
      };
    }
  | {
      type: "dispatch.accepted";
      payload: {
        job_id: string;
        technician_id: string;
        technician_name: string;
        confirmation_phrase: string;
        confirmed_at: string;
        timestamp?: number;
      };
    }
  | {
      type: "dispatch.declined";
      payload: {
        job_id: string;
        technician_id: string;
        technician_name: string;
        timestamp?: number;
      };
    }
  | {
      type: "dispatch.failed";
      payload: {
        job_id: string;
        reason: string;
        timestamp?: number;
      };
    }
  | {
      type: "latency.metric";
      payload: {
        call_id: string;
        turn_id: number;
        stt_latency_ms: number;
        tts_latency_ms: number;
        total_ms: number;
      };
    };

export type EventListener = (event: PakkaEvent) => void;

export interface PakkaEventSource {
  subscribe(listener: EventListener): () => void;
  start(): void;
  pause?(): void;
  resume?(): void;
  restart?(): void;
  destroy(): void;
  isPlaying?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo Timeline Script (40s Booking + 20s Dispatch = ~60s Total)
// ─────────────────────────────────────────────────────────────────────────────

interface ScriptedStep {
  delayMs: number;
  event: PakkaEvent;
}

const DEMO_SCRIPT: ScriptedStep[] = [
  // ── 0. Call Start ────────────────────────────────────────────────────────
  {
    delayMs: 300,
    event: {
      type: "call.started",
      payload: {
        call_id: "demo_call_101",
        caller_number_masked: "+91 98XXXXXX21",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 300,
    event: {
      type: "fsm.state",
      payload: { call_id: "demo_call_101", state: "GREETING" },
    },
  },
  // ── Turn 1: Bot Greeting ──────────────────────────────────────────────────
  {
    delayMs: 600,
    event: {
      type: "bot.speaking",
      payload: {
        call_id: "demo_call_101",
        text: "Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "bot",
        text: "Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?",
        is_disclosure: true,
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  // ── Turn 2: Caller Problem ────────────────────────────────────────────────
  {
    delayMs: 2500,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "caller",
        text: "Geyser paani garam nahi kar raha, bohot thanda paani aa raha hai.",
        language: "hi-IN",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "slot.updated",
      payload: {
        call_id: "demo_call_101",
        field: "problem",
        value: "Geyser not heating (paani thanda)",
      },
    },
  },
  {
    delayMs: 300,
    event: {
      type: "fsm.state",
      payload: { call_id: "demo_call_101", state: "ADDRESS" },
    },
  },
  {
    delayMs: 600,
    event: {
      type: "bot.speaking",
      payload: {
        call_id: "demo_call_101",
        text: "Geyser repair ho jayega ji. Kripya apna address aur paas ka landmark bataiye.",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "bot",
        text: "Geyser repair ho jayega ji. Kripya apna address aur paas ka landmark bataiye.",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  // ── Turn 3: Caller Landmark Address ───────────────────────────────────────
  {
    delayMs: 2800,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "caller",
        text: "Pocket B, Mayur Vihar Phase 2, Mother Dairy ke paas.",
        language: "hi-IN",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "slot.updated",
      payload: {
        call_id: "demo_call_101",
        field: "landmark_address",
        value: "Pocket B, Mayur Vihar Phase 2 (near Mother Dairy)",
      },
    },
  },
  {
    delayMs: 300,
    event: {
      type: "fsm.state",
      payload: { call_id: "demo_call_101", state: "SLOT" },
    },
  },
  {
    delayMs: 600,
    event: {
      type: "bot.speaking",
      payload: {
        call_id: "demo_call_101",
        text: "Theek hai Mayur Vihar Phase 2. Kaunse time slot mein technician bhej doon?",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "bot",
        text: "Theek hai Mayur Vihar Phase 2. Kaunse time slot mein technician bhej doon?",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  // ── Turn 4: Caller Time Slot ──────────────────────────────────────────────
  {
    delayMs: 2400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "caller",
        text: "Kal subah 10 baje bhej dijiye.",
        language: "hi-IN",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "slot.updated",
      payload: {
        call_id: "demo_call_101",
        field: "time_slot",
        value: "Kal Subah (10:00 AM – 12:00 PM)",
      },
    },
  },
  {
    delayMs: 300,
    event: {
      type: "fsm.state",
      payload: { call_id: "demo_call_101", state: "QUOTE" },
    },
  },
  {
    delayMs: 600,
    event: {
      type: "slot.updated",
      payload: {
        call_id: "demo_call_101",
        field: "price_estimate",
        value: "₹350 – ₹500",
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "bot.speaking",
      payload: {
        call_id: "demo_call_101",
        text: "Geyser repair ka anumanit kharcha 350 se 500 rupaye hoga. Kya main booking pakki kar doon?",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "bot",
        text: "Geyser repair ka anumanit kharcha 350 se 500 rupaye hoga. Kya main booking pakki kar doon?",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  // ── Turn 5: Caller Confirmation ───────────────────────────────────────────
  {
    delayMs: 2200,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "caller",
        text: "Haanji, pakka confirm kar dijiye.",
        language: "hi-IN",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "fsm.state",
      payload: { call_id: "demo_call_101", state: "BOOKED" },
    },
  },
  {
    delayMs: 500,
    event: {
      type: "bot.speaking",
      payload: {
        call_id: "demo_call_101",
        text: "Aapki booking pakki ho gayi hai! Mayur Vihar ke liye technician jald hi sampark karega. Dhanyavaad!",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 400,
    event: {
      type: "transcript",
      payload: {
        call_id: "demo_call_101",
        role: "bot",
        text: "Aapki booking pakki ho gayi hai! Mayur Vihar ke liye technician jald hi sampark karega. Dhanyavaad!",
        is_final: true,
        timestamp: Date.now(),
      },
    },
  },
  // ── 6. Job Booked Event & Stamp ───────────────────────────────────────────
  {
    delayMs: 800,
    event: {
      type: "job.booked",
      payload: {
        job_id: "job_demo_101",
        call_id: "demo_call_101",
        summary: "Geyser heating repair",
        problem: "Geyser not heating (paani thanda)",
        landmark_address: "Pocket B, Mayur Vihar Phase 2 (near Mother Dairy)",
        time_slot: "Kal Subah (10:00 AM – 12:00 PM)",
        price_estimate: "₹350 – ₹500",
        price_min: 350,
        price_max: 500,
        customer_name: "Amit Sharma",
        customer_phone_masked: "+91 98XXXXXX21",
      },
    },
  },
  {
    delayMs: 1200,
    event: {
      type: "call.ended",
      payload: {
        call_id: "demo_call_101",
        duration_seconds: 34,
      },
    },
  },
  // ── 7. Dispatch Outbound Cascade ──────────────────────────────────────────
  {
    delayMs: 1800,
    event: {
      type: "dispatch.started",
      payload: {
        job_id: "job_demo_101",
        technician: {
          id: "tech_01",
          name: "Ramesh Kumar",
          phone: "+91 98XXXXXX01",
          specialty: "Geyser Specialist",
          avatar: "R",
        },
        attempt_number: 1,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 1200,
    event: {
      type: "dispatch.ringing",
      payload: {
        job_id: "job_demo_101",
        technician: "Ramesh Kumar",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 2000,
    event: {
      type: "dispatch.transcript",
      payload: {
        job_id: "job_demo_101",
        role: "bot",
        text: "Namaste Ramesh ji, Pakka demo shop ki digital sahayak bol rahi hoon. Ek naya kaam hai. Geyser repair, Mayur Vihar Phase 2, Kal Subah 10 baje. Kya aap kar sakte hain?",
        is_disclosure: true,
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 2500,
    event: {
      type: "dispatch.transcript",
      payload: {
        job_id: "job_demo_101",
        role: "technician",
        text: "Haan ji, pakka. Main subah 10 baje Mayur Vihar pahunch jaunga.",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 1000,
    event: {
      type: "dispatch.transcript",
      payload: {
        job_id: "job_demo_101",
        role: "bot",
        text: "Dhanyavaad. Pakka. Main customer ko bata dungi.",
        timestamp: Date.now(),
      },
    },
  },
  {
    delayMs: 800,
    event: {
      type: "dispatch.accepted",
      payload: {
        job_id: "job_demo_101",
        technician_id: "tech_01",
        technician_name: "Ramesh Kumar",
        confirmation_phrase: "Haan ji, pakka. Main subah 10 baje Mayur Vihar pahunch jaunga.",
        confirmed_at: "10:00 AM",
        timestamp: Date.now(),
      },
    },
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// DemoEventSource Implementation
// ─────────────────────────────────────────────────────────────────────────────

export class DemoEventSource implements PakkaEventSource {
  private listeners: Set<EventListener> = new Set();
  private currentIndex: number = 0;
  private timer: NodeJS.Timeout | null = null;
  public isPlaying: boolean = false;
  private isDestroyed: boolean = false;

  subscribe(listener: EventListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  start(): void {
    if (this.isPlaying || this.isDestroyed) return;
    this.isPlaying = true;
    this.scheduleNext();
  }

  pause(): void {
    this.isPlaying = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  resume(): void {
    if (this.isPlaying || this.isDestroyed) return;
    this.isPlaying = true;
    this.scheduleNext();
  }

  restart(): void {
    this.pause();
    this.currentIndex = 0;
    this.start();
  }

  destroy(): void {
    this.pause();
    this.isDestroyed = true;
    this.listeners.clear();
  }

  private scheduleNext(): void {
    if (!this.isPlaying || this.currentIndex >= DEMO_SCRIPT.length) {
      this.isPlaying = false;
      return;
    }

    const step = DEMO_SCRIPT[this.currentIndex];
    this.timer = setTimeout(() => {
      if (!this.isPlaying) return;

      for (const listener of this.listeners) {
        try {
          listener(step.event);
        } catch (err) {
          console.error("Demo event listener error:", err);
        }
      }

      this.currentIndex++;
      this.scheduleNext();
    }, step.delayMs);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Live WebSocket EventSource
// ─────────────────────────────────────────────────────────────────────────────

export class LiveWSEventSource implements PakkaEventSource {
  private ws: WebSocket | null = null;
  private listeners: Set<EventListener> = new Set();
  public isPlaying: boolean = true;
  private url: string;
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor(url?: string) {
    const defaultWs =
      typeof window !== "undefined"
        ? `ws://${window.location.hostname}:8000/ws/events`
        : "ws://localhost:8000/ws/events";
    this.url = url || defaultWs;
  }

  subscribe(listener: EventListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  start(): void {
    if (typeof window === "undefined" || this.ws) return;
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onmessage = (evt) => {
        try {
          const raw = JSON.parse(evt.data);
          const event: PakkaEvent = {
            type: raw.event || raw.type,
            payload: raw.data || raw.payload || raw,
          };
          for (const listener of this.listeners) {
            listener(event);
          }
        } catch {
          // Ignore non-json frames
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
        this.reconnectTimer = setTimeout(() => this.start(), 3000);
      };
    } catch (err) {
      console.warn("Live WS connection failed, retrying in 3s:", err);
      this.reconnectTimer = setTimeout(() => this.start(), 3000);
    }
  }

  destroy(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }
}
