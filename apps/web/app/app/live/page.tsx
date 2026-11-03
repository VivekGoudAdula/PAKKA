"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  RotateCcw,
  Phone,
  PhoneCall,
  User,
  MapPin,
  Clock,
  IndianRupee,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  Volume2,
  Radio,
  Sparkles,
  Bot,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { useModeStore } from "@/lib/stores/mode-store";
import {
  DemoEventSource,
  LiveWSEventSource,
  PakkaEvent,
  PakkaEventSource,
} from "@/lib/events";

interface TranscriptItem {
  id: string;
  role: "caller" | "bot" | "technician";
  text: string;
  timestamp: string;
  is_disclosure?: boolean;
}

interface DispatchInfo {
  technicianId?: string;
  technicianName?: string;
  technicianPhone?: string;
  specialty?: string;
  avatar?: string;
  attemptNumber: number;
  status: "idle" | "ringing" | "in_progress" | "accepted" | "declined" | "failed";
  confirmationPhrase?: string;
  confirmedAt?: string;
}

const FSM_STEPS = [
  { id: "GREETING", label: "Greeting" },
  { id: "PROBLEM", label: "Problem" },
  { id: "ADDRESS", label: "Address" },
  { id: "SLOT", label: "Time Slot" },
  { id: "QUOTE", label: "Quote" },
  { id: "CONFIRM", label: "Confirm" },
  { id: "BOOKED", label: "Booked" },
] as const;

export default function LiveConsolePage() {
  const { mode } = useModeStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [fsmState, setFsmState] = useState<string>("GREETING");
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [hasBargeIn, setHasBargeIn] = useState(false);

  // Slots
  const [problem, setProblem] = useState("");
  const [landmarkAddress, setLandmarkAddress] = useState("");
  const [timeSlot, setTimeSlot] = useState("");
  const [priceEstimate, setPriceEstimate] = useState("");

  // Job & Booking
  const [isBooked, setIsBooked] = useState(false);
  const [bookedJobId, setBookedJobId] = useState<string | null>(null);

  // Dispatch Cascade State
  const [dispatch, setDispatch] = useState<DispatchInfo>({
    attemptNumber: 1,
    status: "idle",
  });
  const [dispatchTranscripts, setDispatchTranscripts] = useState<TranscriptItem[]>([]);

  // Emergency / Urgent Handoff
  const [isUrgentHandoff, setIsUrgentHandoff] = useState(false);
  const [handoffReason, setHandoffReason] = useState<string | null>(null);

  // Latencies (only populated in live mode)
  const [latencies, setLatencies] = useState<{ stt?: number; tts?: number; total?: number }>({});

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<PakkaEventSource | null>(null);

  const handleEvent = useCallback((event: PakkaEvent) => {
    const timeStr = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    switch (event.type) {
      case "call.started":
        setFsmState("GREETING");
        setIsBooked(false);
        setIsUrgentHandoff(false);
        setHasBargeIn(false);
        break;

      case "fsm.state":
        setFsmState(event.payload.state);
        if (event.payload.state === "BOOKED") {
          setIsBooked(true);
        }
        break;

      case "bot.speaking":
        setIsBotSpeaking(true);
        setTimeout(() => setIsBotSpeaking(false), 2200);
        break;

      case "barge_in":
        setIsBotSpeaking(false);
        setHasBargeIn(true);
        setTimeout(() => setHasBargeIn(false), 3000);
        break;

      case "transcript":
        setIsBotSpeaking(false);
        setTranscripts((prev) => [
          ...prev,
          {
            id: `tr_${Date.now()}_${Math.random()}`,
            role: event.payload.role,
            text: event.payload.text,
            is_disclosure: event.payload.is_disclosure,
            timestamp: timeStr,
          },
        ]);
        break;

      case "slot.updated":
        if (event.payload.field === "problem") setProblem(event.payload.value);
        if (event.payload.field === "landmark_address") setLandmarkAddress(event.payload.value);
        if (event.payload.field === "time_slot") setTimeSlot(event.payload.value);
        if (event.payload.field === "price_estimate") setPriceEstimate(event.payload.value);
        break;

      case "job.booked":
        setIsBooked(true);
        setBookedJobId(event.payload.job_id);
        setProblem(event.payload.problem || event.payload.summary);
        setLandmarkAddress(event.payload.landmark_address);
        setTimeSlot(event.payload.time_slot);
        setPriceEstimate(event.payload.price_estimate);
        break;

      case "call.handoff":
        setIsUrgentHandoff(true);
        setHandoffReason(event.payload.reason);
        break;

      case "dispatch.started":
        setDispatch({
          technicianId: event.payload.technician.id,
          technicianName: event.payload.technician.name,
          technicianPhone: event.payload.technician.phone,
          specialty: event.payload.technician.specialty,
          avatar: event.payload.technician.avatar || event.payload.technician.name.charAt(0),
          attemptNumber: event.payload.attempt_number,
          status: "ringing",
        });
        break;

      case "dispatch.ringing":
        setDispatch((prev) => ({ ...prev, status: "ringing" }));
        break;

      case "dispatch.transcript":
        setDispatch((prev) => ({ ...prev, status: "in_progress" }));
        setDispatchTranscripts((prev) => [
          ...prev,
          {
            id: `disp_tr_${Date.now()}_${Math.random()}`,
            role: event.payload.role,
            text: event.payload.text,
            is_disclosure: event.payload.is_disclosure,
            timestamp: timeStr,
          },
        ]);
        break;

      case "dispatch.accepted":
        setDispatch((prev) => ({
          ...prev,
          status: "accepted",
          confirmationPhrase: event.payload.confirmation_phrase,
          confirmedAt: event.payload.confirmed_at,
        }));
        break;

      case "dispatch.declined":
        setDispatch((prev) => ({ ...prev, status: "declined" }));
        break;

      case "dispatch.failed":
        setDispatch((prev) => ({ ...prev, status: "failed" }));
        break;

      case "latency.metric":
        setLatencies({
          stt: event.payload.stt_latency_ms,
          tts: event.payload.tts_latency_ms,
          total: event.payload.total_ms,
        });
        break;
    }
  }, []);

  // Auto-scroll transcripts
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, dispatchTranscripts]);

  // Initialize EventSource
  useEffect(() => {
    let source: PakkaEventSource;

    if (mode === "LIVE") {
      source = new LiveWSEventSource();
    } else {
      source = new DemoEventSource();
    }
    eventSourceRef.current = source;

    const unsubscribe = source.subscribe((event: PakkaEvent) => {
      handleEvent(event);
    });

    if (mode === "DEMO") {
      source.start();
    }

    return () => {
      unsubscribe();
      source.destroy();
    };
  }, [mode, handleEvent]);

  const handlePlayPause = () => {
    if (!eventSourceRef.current) return;
    if (isPlaying) {
      eventSourceRef.current.pause?.();
      setIsPlaying(false);
    } else {
      eventSourceRef.current.resume?.();
      setIsPlaying(true);
    }
  };

  const handleRestart = () => {
    // Reset local state
    setTranscripts([]);
    setDispatchTranscripts([]);
    setProblem("");
    setLandmarkAddress("");
    setTimeSlot("");
    setPriceEstimate("");
    setIsBooked(false);
    setBookedJobId(null);
    setIsUrgentHandoff(false);
    setFsmState("GREETING");
    setDispatch({ attemptNumber: 1, status: "idle" });

    eventSourceRef.current?.restart?.();
    setIsPlaying(true);
  };

  const currentStepIndex = FSM_STEPS.findIndex((s) => s.id === fsmState);

  return (
    <div className="space-y-6 pb-20 md:pb-8">
      {/* ── Top Bar Header & Controls ───────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-card border border-border shadow-xs">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Radio className="h-5 w-5" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-foreground">
                Live Voice Console
              </h1>
              <Badge
                variant="outline"
                className="bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800 text-[11px] font-semibold"
              >
                Inbound Active
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {mode === "DEMO"
                ? "Simulated 40s booking + 20s technician dispatch call"
                : "Realtime WebSocket connected to Exotel Voicebot"}
            </p>
          </div>
        </div>

        {/* Demo Script Controls & Mode Badge */}
        <div className="flex items-center gap-2 flex-wrap">
          {mode === "DEMO" && (
            <Badge
              variant="outline"
              className="bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800 font-medium text-xs px-2.5 py-1"
            >
              Scripted demo, not a live call
            </Badge>
          )}

          {/* Latency Chips (Shown in LIVE mode or when metrics exist) */}
          {mode === "LIVE" && latencies.stt !== undefined && (
            <div className="flex items-center gap-1.5 text-xs font-mono bg-muted px-2.5 py-1 rounded-md text-muted-foreground">
              <Zap className="h-3 w-3 text-amber-500" />
              <span>STT: {Math.round(latencies.stt)}ms</span>
              {latencies.tts !== undefined && <span>| TTS: {Math.round(latencies.tts)}ms</span>}
            </div>
          )}

          {mode === "DEMO" && (
            <div className="flex items-center gap-1.5 bg-muted/60 p-1 rounded-lg border border-border">
              <Button
                size="sm"
                variant={isPlaying ? "secondary" : "default"}
                onClick={handlePlayPause}
                className="h-8 gap-1.5 text-xs font-medium"
              >
                {isPlaying ? (
                  <>
                    <Pause className="h-3.5 w-3.5" /> Pause
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5" /> Play
                  </>
                )}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleRestart}
                className="h-8 gap-1.5 text-xs"
                title="Restart Script"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Restart
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* ── Emergency Safety Hazard Warning Banner ──────────────────────────── */}
      <AnimatePresence>
        {isUrgentHandoff && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-xl border-2 border-red-500 bg-red-50 dark:bg-red-950/50 text-red-950 dark:text-red-100 flex items-start gap-3 shadow-md"
          >
            <AlertTriangle className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-wide uppercase text-red-700 dark:text-red-300">
                  CRITICAL SAFETY HAZARD DETECTED
                </span>
                <Badge variant="destructive" className="text-[10px] uppercase font-bold">
                  Owner Handoff
                </Badge>
              </div>
              <p className="text-sm font-semibold mt-1">
                &ldquo;Kripya pehle main switch band kar dijiye aur geyser se door rahiye. Main
                abhi malik ko bata rahi hoon, woh turant aapko phone karenge.&rdquo;
              </p>
              <p className="text-xs text-red-700/80 dark:text-red-300/80 mt-1">
                {handoffReason ? `Reason: ${handoffReason}. ` : ""}
                Routine booking halted immediately. Alert SMS &amp; voice call dispatched to business owner.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── FSM Stepper Bar ─────────────────────────────────────────────────── */}
      <div className="p-3 rounded-xl bg-card border border-border shadow-2xs overflow-x-auto">
        <div className="flex items-center justify-between min-w-[560px] gap-2">
          {FSM_STEPS.map((step, idx) => {
            const isCompleted = currentStepIndex > idx || isBooked;
            const isCurrent = currentStepIndex === idx && !isBooked;

            return (
              <div key={step.id} className="flex items-center gap-2 flex-1 last:flex-none">
                <div
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                    isCompleted &&
                      "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
                    isCurrent &&
                      "bg-primary text-primary-foreground font-semibold shadow-xs ring-2 ring-primary/20",
                    !isCompleted &&
                      !isCurrent &&
                      "bg-muted/50 text-muted-foreground border border-transparent"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : (
                    <span className="h-4 w-4 rounded-full bg-background/50 flex items-center justify-center text-[10px] font-bold">
                      {idx + 1}
                    </span>
                  )}
                  <span className="truncate">{step.label}</span>
                </div>
                {idx < FSM_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "h-0.5 flex-1 transition-colors",
                      isCompleted ? "bg-emerald-400" : "bg-muted"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Main Two-Column Layout ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── Left Column: Live Call Transcript (7 cols) ────────────────────── */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="border-border shadow-sm">
            <CardHeader className="py-3 px-4 border-b border-border bg-muted/30 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <PhoneCall className="h-4 w-4 text-primary" />
                <CardTitle className="text-sm font-semibold">
                  Customer Inbound Call (+91 98XXXXXX21)
                </CardTitle>
              </div>

              <div className="flex items-center gap-2">
                {isBotSpeaking && (
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium animate-pulse">
                    <Volume2 className="h-3.5 w-3.5" />
                    <span>Speaking</span>
                  </div>
                )}
                {hasBargeIn && (
                  <Badge variant="secondary" className="text-[10px] bg-amber-100 text-amber-800 border-amber-300">
                    Barge-in
                  </Badge>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-4 min-h-[380px] max-h-[500px] overflow-y-auto space-y-3 font-sans">
              {transcripts.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
                  <Phone className="h-8 w-8 mb-2 opacity-30 animate-bounce" />
                  <p className="text-sm font-medium">Connecting voice stream...</p>
                  <p className="text-xs text-muted-foreground/70">
                    Caller utterance will appear in realtime
                  </p>
                </div>
              ) : (
                transcripts.map((msg) => {
                  const isBot = msg.role === "bot";
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={cn(
                        "daisy-chat",
                        isBot ? "daisy-chat-start" : "daisy-chat-end"
                      )}
                    >
                      <div className="daisy-chat-header text-[11px] text-muted-foreground mb-1 flex items-center gap-1.5">
                        {isBot ? (
                          <>
                            <Bot className="h-3 w-3 text-primary" />
                            <span className="font-semibold text-foreground">Pakka Digital Sahayak</span>
                            {msg.is_disclosure && (
                              <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.2 rounded font-medium">
                                AI Disclosed
                              </span>
                            )}
                          </>
                        ) : (
                          <>
                            <User className="h-3 w-3" />
                            <span className="font-semibold text-foreground">Caller</span>
                          </>
                        )}
                        <time className="text-[10px] opacity-60 ml-1">{msg.timestamp}</time>
                      </div>

                      <div
                        className={cn(
                          "daisy-chat-bubble text-sm leading-relaxed max-w-[85%] rounded-2xl p-3 shadow-2xs",
                          isBot
                            ? "bg-muted text-foreground border border-border"
                            : "bg-primary text-primary-foreground font-medium"
                        )}
                      >
                        {msg.text}
                      </div>
                    </motion.div>
                  );
                })
              )}
              <div ref={transcriptEndRef} />
            </CardContent>
          </Card>

          {/* ── Technician Dispatch Card (Outbound Dialogue) ──────────────────── */}
          <Card
            className={cn(
              "border-border shadow-sm transition-all",
              dispatch.status === "ringing" && "ring-2 ring-primary/40",
              dispatch.status === "accepted" && "border-emerald-300 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/10"
            )}
          >
            <CardHeader className="py-3 px-4 border-b border-border bg-muted/30 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Wrench className="h-4 w-4 text-emerald-600" />
                <CardTitle className="text-sm font-semibold">
                  Technician Voice Dispatch
                </CardTitle>
              </div>

              {dispatch.status === "ringing" && (
                <Badge className="bg-amber-500 hover:bg-amber-600 text-white animate-pulse gap-1 text-[11px]">
                  <PhoneCall className="h-3 w-3 animate-bounce" /> Ringing Specialist (Attempt {dispatch.attemptNumber}/3)
                </Badge>
              )}
              {dispatch.status === "in_progress" && (
                <Badge className="bg-blue-600 hover:bg-blue-700 text-white text-[11px]">
                  Connected &amp; Reading Job
                </Badge>
              )}
              {dispatch.status === "accepted" && (
                <Badge className="bg-emerald-600 text-white text-[11px] gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Accepted ({dispatch.confirmedAt})
                </Badge>
              )}
              {dispatch.status === "idle" && (
                <span className="text-xs text-muted-foreground">Waiting for booking</span>
              )}
            </CardHeader>

            <CardContent className="p-4 space-y-3">
              {dispatch.status === "idle" ? (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  Voice dispatch initiates automatically as soon as the customer confirms the booking.
                </div>
              ) : (
                <>
                  {/* Technician Profile Card */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-border">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 font-bold flex items-center justify-center text-base">
                        {dispatch.avatar || "R"}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-foreground">
                          {dispatch.technicianName}
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                          <span>{dispatch.specialty}</span>
                          <span>•</span>
                          <span>{dispatch.technicianPhone}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[11px] font-bold text-muted-foreground uppercase">
                        Attempt {dispatch.attemptNumber} of 3
                      </span>
                    </div>
                  </div>

                  {/* Rolling Dispatch Transcript */}
                  <div className="space-y-2 pt-1 font-sans">
                    {dispatchTranscripts.map((t) => {
                      const isBot = t.role === "bot";
                      return (
                        <div
                          key={t.id}
                          className={cn(
                            "daisy-chat",
                            isBot ? "daisy-chat-start" : "daisy-chat-end"
                          )}
                        >
                          <div className="daisy-chat-header text-[10px] text-muted-foreground mb-0.5">
                            {isBot ? "Pakka Digital Sahayak" : dispatch.technicianName}
                          </div>
                          <div
                            className={cn(
                              "daisy-chat-bubble text-xs leading-relaxed rounded-xl p-2.5",
                              isBot
                                ? "bg-muted text-foreground border border-border"
                                : "bg-emerald-700 text-white font-medium"
                            )}
                          >
                            {t.text}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Confirmed Quote Callout */}
                  {dispatch.status === "accepted" && dispatch.confirmationPhrase && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="p-3 rounded-lg bg-emerald-100/70 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-xs text-emerald-950 dark:text-emerald-100 flex items-center gap-2"
                    >
                      <Sparkles className="h-4 w-4 text-emerald-600 shrink-0" />
                      <div>
                        <span className="font-semibold">Voice Confirmation:</span> &ldquo;
                        {dispatch.confirmationPhrase}&rdquo;
                      </div>
                    </motion.div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Right Column: Slots, FSM & Pakka Stamp (5 cols) ───────────────── */}
        <div className="lg:col-span-5 space-y-4">
          {/* Extracted Slots Card */}
          <Card className="border-border shadow-sm">
            <CardHeader className="py-3 px-4 border-b border-border bg-muted/30">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Extracted Slots (Rule-Based)
                </CardTitle>
                <Badge variant="outline" className="text-[10px]">
                  Zero LLM
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-4 space-y-3">
              {/* Problem */}
              <div className="p-3 rounded-xl border border-border bg-card">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground mb-1">
                  <Wrench className="h-3.5 w-3.5 text-primary" />
                  <span>Problem / Service</span>
                </div>
                <div className="text-sm font-bold text-foreground">
                  {problem ? (
                    <span className="text-foreground">{problem}</span>
                  ) : (
                    <span className="text-muted-foreground/50 font-normal italic">
                      Waiting for caller utterance...
                    </span>
                  )}
                </div>
              </div>

              {/* Landmark Address */}
              <div className="p-3 rounded-xl border border-border bg-card">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground mb-1">
                  <MapPin className="h-3.5 w-3.5 text-primary" />
                  <span>Landmark Address</span>
                </div>
                <div className="text-sm font-bold text-foreground">
                  {landmarkAddress ? (
                    <span className="text-foreground">{landmarkAddress}</span>
                  ) : (
                    <span className="text-muted-foreground/50 font-normal italic">
                      Pending location...
                    </span>
                  )}
                </div>
              </div>

              {/* Time Slot */}
              <div className="p-3 rounded-xl border border-border bg-card">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground mb-1">
                  <Clock className="h-3.5 w-3.5 text-primary" />
                  <span>Preferred Slot</span>
                </div>
                <div className="text-sm font-bold text-foreground">
                  {timeSlot ? (
                    <span className="text-foreground">{timeSlot}</span>
                  ) : (
                    <span className="text-muted-foreground/50 font-normal italic">
                      Pending timing...
                    </span>
                  )}
                </div>
              </div>

              {/* Price Range */}
              <div className="p-3 rounded-xl border border-border bg-card">
                <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground mb-1">
                  <IndianRupee className="h-3.5 w-3.5 text-primary" />
                  <span>Price Quote</span>
                </div>
                <div className="text-sm font-bold text-foreground">
                  {priceEstimate ? (
                    <span className="text-emerald-700 dark:text-emerald-400 font-extrabold text-base">
                      {priceEstimate}
                    </span>
                  ) : (
                    <span className="text-muted-foreground/50 font-normal italic">
                      Quote pending...
                    </span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pakka Stamp Spring-In Card */}
          <Card className="border-border shadow-sm text-center p-6 bg-card flex flex-col items-center justify-center min-h-[260px] relative overflow-hidden">
            <AnimatePresence>
              {isBooked ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.5, rotate: -15 }}
                  animate={{ opacity: 1, scale: 1, rotate: -3 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  className="flex flex-col items-center"
                >
                  <PakkaStamp visible={isBooked} variant="success" size="lg" />
                  <div className="mt-4">
                    <div className="text-base font-bold text-emerald-800 dark:text-emerald-300">
                      Job Confirmed &amp; Logged
                    </div>
                    <div className="text-xs text-muted-foreground font-mono mt-0.5">
                      {bookedJobId || "job_demo_101"}
                    </div>
                  </div>
                </motion.div>
              ) : (
                <div className="text-muted-foreground flex flex-col items-center py-6">
                  <div className="w-24 h-24 rounded-full border-2 border-dashed border-border flex items-center justify-center mb-3">
                    <CheckCircle2 className="h-8 w-8 text-muted-foreground/30" />
                  </div>
                  <p className="text-sm font-medium text-foreground">Awaiting Final Confirmation</p>
                  <p className="text-xs text-muted-foreground max-w-[220px] mt-1">
                    Stamp triggers automatically when the caller accepts the price quote.
                  </p>
                </div>
              )}
            </AnimatePresence>
          </Card>
        </div>
      </div>
    </div>
  );
}
