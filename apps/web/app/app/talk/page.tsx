"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  MicOff,
  Square,
  Volume2,
  VolumeX,
  RotateCcw,
  Sparkles,
  Send,
  Keyboard,
  Headphones,
  CheckCircle2,
  Flame,
  Activity,
  Layers,
  UserCheck,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { BrowserAudioRecorder } from "@/lib/audio-recorder";
import { cn } from "@/lib/utils";

// Interaction states
type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "error";

interface ChatMessage {
  id: string;
  role: "user" | "bot";
  text: string;
  timestamp: string;
  audioB64?: string;
  latency?: {
    stt: number;
    tts: number;
    total: number;
  };
  typed?: boolean;
}

interface VoiceSessionSlots {
  problem?: string | null;
  problem_key?: string | null;
  landmark_address?: string | null;
  time_slot?: string | null;
  price_estimate?: string | null;
  ptp_date?: string | null;
  disposition?: string | null;
}

interface TurnApiResponse {
  transcript?: string;
  reply_text: string;
  audio_b64?: string;
  state: string;
  slots?: VoiceSessionSlots;
  is_terminal?: boolean;
  is_urgent?: boolean;
  needs_human?: boolean;
  mode?: string;
  latency_ms?: {
    stt: number;
    tts: number;
    total: number;
  };
}

export default function TalkToPakkaPage() {
  const [flow, setFlow] = useState<"booking" | "collection">("booking");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentState, setCurrentState] = useState<string>("GREETING");
  const [slots, setSlots] = useState<VoiceSessionSlots>({});
  const [isTerminal, setIsTerminal] = useState<boolean>(false);
  const [isUrgent, setIsUrgent] = useState<boolean>(false);
  const [needsHuman, setNeedsHuman] = useState<boolean>(false);
  const [isDryRun, setIsDryRun] = useState<boolean>(true);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);
  const [showTypedInput, setShowTypedInput] = useState<boolean>(false);
  const [typedText, setTypedText] = useState<string>("");
  const [micPermissionDenied, setMicPermissionDenied] = useState<boolean>(false);
  const [usageStats, setUsageStats] = useState<{ calls_last_hour: number; max_calls_per_hour: number }>({
    calls_last_hour: 0,
    max_calls_per_hour: 150,
  });

  const [rmsVolume, setRmsVolume] = useState<number>(0);
  const recorderRef = useRef<BrowserAudioRecorder | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Auto-scroll chat stream
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, voiceState]);

  // Refresh usage stats
  const refreshUsage = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/voice/usage`);
      if (res.ok) {
        const u = await res.json();
        setUsageStats({
          calls_last_hour: u.calls_last_hour ?? 0,
          max_calls_per_hour: u.max_calls_per_hour ?? 150,
        });
      }
    } catch {
      // Ignore background usage fetch error
    }
  }, [API_URL]);

  // Play returned base64 WAV audio
  const playAudioB64 = useCallback((b64Wav: string) => {
    if (audioMuted) {
      setVoiceState("idle");
      return;
    }

    try {
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      const audio = audioPlayerRef.current;
      audio.src = `data:audio/wav;base64,${b64Wav}`;
      setVoiceState("speaking");

      audio.onended = () => {
        setVoiceState("idle");
      };
      audio.onerror = () => {
        setVoiceState("idle");
      };

      audio.play().catch(() => {
        // Autoplay may be restricted before user gesture
        setVoiceState("idle");
      });
    } catch {
      setVoiceState("idle");
    }
  }, [audioMuted]);

  // Fetch initial usage stats & initialize session
  const initializeSession = useCallback(async (selectedFlow: "booking" | "collection") => {
    try {
      setVoiceState("thinking");
      const res = await fetch(`${API_URL}/api/voice/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flow: selectedFlow, customer: "Ramesh", tone_level: 1 }),
      });

      if (!res.ok) {
        throw new Error(`Failed to start session: ${res.statusText}`);
      }

      const data = await res.json();
      setSessionId(data.session_id);
      setCurrentState(data.state);
      setIsDryRun(data.mode === "dry_run" || data.mode === "mock");
      setIsTerminal(false);
      setIsUrgent(false);
      setNeedsHuman(false);
      setSlots({});

      // Set initial greeting
      const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages([
        {
          id: "msg_init",
          role: "bot",
          text: data.initial_reply,
          timestamp: nowStr,
          audioB64: data.initial_audio_b64,
        },
      ]);

      // Play greeting audio if available
      if (data.initial_audio_b64 && !audioMuted) {
        playAudioB64(data.initial_audio_b64);
      } else {
        setVoiceState("idle");
      }

      // Refresh usage stats
      refreshUsage();
    } catch (err: unknown) {
      console.error(err);
      toast.error("Could not connect to Pakka Voice backend.");
      setVoiceState("error");
    }
  }, [API_URL, audioMuted, playAudioB64, refreshUsage]);

  // Initial load effect
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const res = await fetch(`${API_URL}/api/voice/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ flow, customer: "Ramesh", tone_level: 1 }),
        });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (!active) return;
        setSessionId(data.session_id);
        setCurrentState(data.state);
        setIsDryRun(data.mode === "dry_run" || data.mode === "mock");
        setIsTerminal(false);
        setIsUrgent(false);
        setNeedsHuman(false);
        setSlots({});
        const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setMessages([
          {
            id: "msg_init",
            role: "bot",
            text: data.initial_reply,
            timestamp: nowStr,
            audioB64: data.initial_audio_b64,
          },
        ]);
        if (data.initial_audio_b64 && !audioMuted) {
          playAudioB64(data.initial_audio_b64);
        } else {
          setVoiceState("idle");
        }
        void refreshUsage();
      } catch (err: unknown) {
        if (!active) return;
        console.error(err);
        toast.error("Could not connect to Pakka Voice backend.");
        setVoiceState("error");
      }
    };
    void run();
    return () => {
      active = false;
    };
  }, [flow, API_URL, audioMuted, playAudioB64, refreshUsage]);

  // Unified Handler for Turn Result
  const handleTurnResponse = useCallback((turnResult: TurnApiResponse, typed = false) => {
    const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // 1. Add User message
    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      text: turnResult.transcript || "(speech)",
      timestamp: nowStr,
      typed,
    };

    // 2. Add Bot message
    const botMsg: ChatMessage = {
      id: `bot_${Date.now()}`,
      role: "bot",
      text: turnResult.reply_text,
      timestamp: nowStr,
      audioB64: turnResult.audio_b64,
      latency: turnResult.latency_ms,
    };

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setCurrentState(turnResult.state);
    setSlots(turnResult.slots || {});
    setIsTerminal(Boolean(turnResult.is_terminal));
    setIsUrgent(Boolean(turnResult.is_urgent));
    setNeedsHuman(Boolean(turnResult.needs_human));
    if (turnResult.mode) {
      setIsDryRun(turnResult.mode === "dry_run" || turnResult.mode === "mock");
    }

    void refreshUsage();

    // Play bot speech
    if (turnResult.audio_b64 && !audioMuted) {
      playAudioB64(turnResult.audio_b64);
    } else {
      setVoiceState("idle");
    }
  }, [audioMuted, playAudioB64, refreshUsage]);

  // Stop Mic Recording and send turn
  const stopRecordingAndSubmit = useCallback(async () => {
    if (!recorderRef.current) return;

    setVoiceState("thinking");
    setRmsVolume(0);

    try {
      const wavBlob = await recorderRef.current.stop();
      recorderRef.current = null;

      if (!sessionId) {
        toast.error("Session missing. Reconnecting...");
        void initializeSession(flow);
        return;
      }

      // Check minimum length (must be at least ~5KB for 0.3s)
      if (wavBlob.size < 4000) {
        toast.info("Audio too short or silent. Please try again.");
        setVoiceState("idle");
        return;
      }

      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("audio", wavBlob, "turn.wav");

      const res = await fetch(`${API_URL}/api/voice/turn`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Voice turn processing failed");
      }

      const turnResult = await res.json();
      handleTurnResponse(turnResult);
    } catch (err: unknown) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Error processing voice turn");
      setVoiceState("idle");
    }
  }, [API_URL, flow, handleTurnResponse, initializeSession, sessionId]);

  // Start Mic Recording
  const startRecording = useCallback(async () => {
    if (isTerminal) return;

    // Stop speaking if playing
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    try {
      setMicPermissionDenied(false);
      const recorder = new BrowserAudioRecorder({
        sampleRate: 16000,
        silenceThresholdMs: 1400,
        silenceRmsFloor: 0.018,
        maxDurationMs: 30000,
        onRmsUpdate: (rms) => setRmsVolume(rms),
        onSilenceTimeout: () => {
          void stopRecordingAndSubmit();
        },
        onMaxDuration: () => {
          void stopRecordingAndSubmit();
        },
      });

      recorderRef.current = recorder;
      await recorder.start();
      setVoiceState("listening");
    } catch (err: unknown) {
      console.error("Mic error:", err);
      setMicPermissionDenied(true);
      setShowTypedInput(true);
      setVoiceState("idle");
      toast.error("Microphone access denied or unavailable. Please use the typed input.");
    }
  }, [isTerminal, stopRecordingAndSubmit]);

  // Handle Typed Turn Submission
  const handleTypedSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const text = typedText.trim();
    if (!text || !sessionId || voiceState === "thinking") return;

    setTypedText("");
    setVoiceState("thinking");

    try {
      const res = await fetch(`${API_URL}/api/voice/text-turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, text }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Typed turn failed");
      }

      const turnResult = await res.json();
      handleTurnResponse(turnResult, true);
    } catch (err: unknown) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : "Turn failed");
      setVoiceState("idle");
    }
  };

  // Toggle Tap-to-Talk via Mic button or Space bar
  const toggleRecording = useCallback(() => {
    if (voiceState === "listening") {
      void stopRecordingAndSubmit();
    } else if (voiceState === "idle" || voiceState === "error") {
      void startRecording();
    }
  }, [voiceState]);

  // Spacebar hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.code === "Space" &&
        !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        toggleRecording();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleRecording]);

  // Realtime Waveform Visualization on Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (voiceState === "listening") {
        // Active caller speaking visualization
        const bars = 24;
        const width = canvas.width / bars;
        const baseH = canvas.height * 0.15;
        const mult = Math.min(1.0, rmsVolume * 8.0);

        ctx.fillStyle = "rgba(255, 159, 28, 0.85)";
        for (let i = 0; i < bars; i++) {
          const wave = Math.sin(Date.now() * 0.015 + i * 0.4) * 0.5 + 0.5;
          const h = Math.max(4, canvas.height * mult * wave + baseH);
          const y = (canvas.height - h) / 2;
          ctx.beginPath();
          ctx.roundRect(i * width + 2, y, width - 4, h, 3);
          ctx.fill();
        }
      } else if (voiceState === "speaking") {
        // Bot speaking smooth pulse
        const bars = 24;
        const width = canvas.width / bars;
        ctx.fillStyle = "rgba(46, 196, 182, 0.75)";
        for (let i = 0; i < bars; i++) {
          const wave = Math.sin(Date.now() * 0.008 + i * 0.3) * 0.5 + 0.5;
          const h = Math.max(6, canvas.height * 0.45 * wave);
          const y = (canvas.height - h) / 2;
          ctx.beginPath();
          ctx.roundRect(i * width + 2, y, width - 4, h, 3);
          ctx.fill();
        }
      } else if (voiceState === "thinking") {
        // Thinking pulsing dots
        ctx.fillStyle = "rgba(100, 116, 139, 0.5)";
        const wave = Math.sin(Date.now() * 0.006) * 10;
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2 + wave, 6, 0, Math.PI * 2);
        ctx.fill();
      }

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [voiceState, rmsVolume]);

  const isBooked = currentState === "BOOKED";

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto w-full pb-12">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground flex items-center gap-2">
              <Sparkles className="h-7 w-7 text-primary animate-pulse" />
              Talk to Pakka
            </h1>
            <Badge
              variant={isDryRun ? "outline" : "default"}
              className={cn(
                "font-mono text-[11px] uppercase tracking-wider",
                isDryRun
                  ? "bg-amber-500/10 text-amber-700 border-amber-500/30 dark:text-amber-400"
                  : "bg-emerald-500/10 text-emerald-700 border-emerald-500/30 dark:text-emerald-400"
              )}
            >
              {isDryRun ? "Simulated speech, not Gnani" : "Live Gnani REST"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Realtime browser voice assistant for Delhi NCR plumbers & local service businesses.
          </p>
        </div>

        {/* Mode & Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <Tabs
            value={flow}
            onValueChange={(val) => {
              const f = val as "booking" | "collection";
              setFlow(f);
              initializeSession(f);
            }}
            className="w-auto"
          >
            <TabsList className="bg-surface border border-border h-9 p-0.5">
              <TabsTrigger value="booking" className="text-xs font-semibold px-3 h-8">
                Book a Job
              </TabsTrigger>
              <TabsTrigger value="collection" className="text-xs font-semibold px-3 h-8">
                Payment Reminder
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setAudioMuted(!audioMuted)}
            className="h-9 px-3 gap-1.5 text-xs"
            title={audioMuted ? "Unmute Bot Voice" : "Mute Bot Voice"}
          >
            {audioMuted ? <VolumeX className="h-4 w-4 text-destructive" /> : <Volume2 className="h-4 w-4" />}
            <span className="hidden sm:inline">{audioMuted ? "Muted" : "Sound On"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => initializeSession(flow)}
            className="h-9 px-3 gap-1.5 text-xs"
            title="Start fresh conversation"
          >
            <RotateCcw className="h-4 w-4" />
            <span className="hidden sm:inline">Reset</span>
          </Button>
        </div>
      </div>

      {/* Warning Banners (Emergency Hazard / Human Escalation / Mic Denied / Usage) */}
      {isUrgent && (
        <div className="bg-destructive/10 border-2 border-destructive/40 rounded-xl p-4 flex items-start gap-3.5 animate-bounce-subtle">
          <Flame className="h-6 w-6 text-destructive shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-bold text-destructive text-sm uppercase tracking-wide">
              EMERGENCY HAZARD TRIGGERED — URGENT ESCALATION
            </h4>
            <p className="text-xs text-destructive/90 mt-0.5 leading-relaxed">
              Caller reported immediate danger (current / spark / gas / flooding). Bot instructed to switch off mains & geyser immediately. Emergency owner callback initiated.
            </p>
          </div>
        </div>
      )}

      {needsHuman && !isUrgent && (
        <div className="bg-primary/10 border border-primary/30 rounded-xl p-3.5 flex items-center justify-between text-xs text-foreground">
          <div className="flex items-center gap-2.5">
            <UserCheck className="h-5 w-5 text-primary shrink-0" />
            <span>Human callback requested or AI inquiry answered. Escalation dispatched to business owner.</span>
          </div>
        </div>
      )}

      {micPermissionDenied && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex items-center justify-between text-xs text-amber-700 dark:text-amber-400">
          <div className="flex items-center gap-2">
            <MicOff className="h-4 w-4 shrink-0 text-amber-600" />
            <span>Microphone blocked or unavailable. Type your message below to continue.</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-[11px]"
            onClick={() => setShowTypedInput(true)}
          >
            Type instead
          </Button>
        </div>
      )}

      {/* Main Grid: Left Chat & Voice Console | Right FSM & Slots */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Dialogue & Interactive Mic */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <Card className="border-border shadow-xs bg-surface flex flex-col h-[520px] overflow-hidden">
            {/* Session Sub-header */}
            <div className="px-4 py-2.5 bg-surface-2/60 border-b border-border/80 flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex items-center gap-2 font-mono">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Session: {sessionId ? sessionId.slice(0, 14) + "..." : "Connecting..."}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 font-mono text-[11px]">
                  <Headphones className="h-3 w-3 text-primary" />
                  Headphones recommended
                </span>
                <span className="font-mono text-[11px]">
                  {usageStats.calls_last_hour}/{usageStats.max_calls_per_hour} calls/hr
                </span>
              </div>
            </div>

            {/* Chat Messages Stream (Prefixed daisyUI bubbles) */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
              {messages.map((msg) => {
                const isBot = msg.role === "bot";
                return (
                  <div
                    key={msg.id}
                    className={cn(
                      "daisy-chat",
                      isBot ? "daisy-chat-start" : "daisy-chat-end"
                    )}
                  >
                    <div className="daisy-chat-image">
                      <div
                        className={cn(
                          "w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold border",
                          isBot
                            ? "bg-primary text-white border-primary"
                            : "bg-surface-2 text-foreground border-border"
                        )}
                      >
                        {isBot ? "P" : "C"}
                      </div>
                    </div>

                    <div className="daisy-chat-header text-[11px] text-muted-foreground mb-1">
                      {isBot ? "Pakka Sahayak" : "You (Caller)"}
                      <time className="text-[10px] opacity-60 ml-1.5">{msg.timestamp}</time>
                      {msg.typed && (
                        <span className="ml-1 text-[10px] text-muted-foreground italic">(typed)</span>
                      )}
                    </div>

                    <div
                      className={cn(
                        "daisy-chat-bubble font-sans text-sm leading-relaxed max-w-[85%] rounded-2xl px-4 py-2.5",
                        isBot
                          ? "bg-primary/10 text-foreground border border-primary/20"
                          : "bg-card text-foreground border border-border"
                      )}
                    >
                      {msg.text}

                      {/* Bot Audio Replay Button */}
                      {isBot && msg.audioB64 && (
                        <div className="mt-2 pt-1 border-t border-primary/10 flex items-center justify-between">
                          <button
                            type="button"
                            onClick={() => playAudioB64(msg.audioB64!)}
                            className="inline-flex items-center gap-1 text-[11px] text-primary font-medium hover:underline cursor-pointer"
                          >
                            <Volume2 className="h-3 w-3" /> Replay Voice
                          </button>
                          {msg.latency && (
                            <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
                              {msg.latency.stt > 0 && <span>STT: {msg.latency.stt}ms</span>}
                              <span>TTS: {msg.latency.tts}ms</span>
                              <span className="font-bold text-foreground">Σ {msg.latency.total}ms</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Bot Thinking Skeleton indicator */}
              {voiceState === "thinking" && (
                <div className="daisy-chat daisy-chat-start">
                  <div className="daisy-chat-image">
                    <div className="w-7 h-7 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">
                      ...
                    </div>
                  </div>
                  <div className="daisy-chat-bubble bg-primary/10 border border-primary/20 text-xs py-2 px-3 text-muted-foreground flex items-center gap-2">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary animate-ping" />
                    <span>Pakka is listening & thinking...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Bottom Mic & Controls Bar */}
            <div className="p-3 bg-surface border-t border-border flex flex-col gap-2.5">
              {/* Waveform Canvas */}
              <div className="w-full h-8 bg-surface-2/40 rounded-lg overflow-hidden flex items-center justify-center relative">
                <canvas ref={canvasRef} width={400} height={32} className="w-full h-full" />
                {voiceState === "idle" && (
                  <span className="absolute text-[11px] font-mono text-muted-foreground/70">
                    Press Space or tap Mic to talk
                  </span>
                )}
              </div>

              {/* Controls Row */}
              <div className="flex items-center justify-between gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowTypedInput(!showTypedInput)}
                  className="h-10 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
                >
                  <Keyboard className="h-4 w-4" />
                  <span>{showTypedInput ? "Hide text" : "Type instead"}</span>
                </Button>

                {/* Central Tap-to-Talk Mic Button */}
                <div className="relative flex items-center justify-center">
                  {voiceState === "listening" && (
                    <span className="absolute -inset-2.5 rounded-full bg-primary/30 animate-ping" />
                  )}
                  {voiceState === "speaking" && (
                    <span className="absolute -inset-2 rounded-full bg-emerald-500/20 animate-pulse" />
                  )}

                  <Button
                    type="button"
                    size="lg"
                    onClick={toggleRecording}
                    disabled={voiceState === "thinking" || isTerminal}
                    className={cn(
                      "h-14 w-14 rounded-full p-0 shadow-md transition-all duration-200 relative z-10",
                      voiceState === "listening"
                        ? "bg-destructive text-destructive-foreground hover:bg-destructive/90 scale-105"
                        : voiceState === "speaking"
                        ? "bg-emerald-600 text-white hover:bg-emerald-700"
                        : "bg-primary text-primary-foreground hover:bg-primary/90"
                    )}
                    aria-label={voiceState === "listening" ? "Stop recording" : "Start speaking"}
                  >
                    {voiceState === "listening" ? (
                      <Square className="h-6 w-6" />
                    ) : voiceState === "speaking" ? (
                      <Volume2 className="h-6 w-6 animate-bounce" />
                    ) : (
                      <Mic className="h-6 w-6" />
                    )}
                  </Button>
                </div>

                <div className="w-24 text-right">
                  <span className="font-mono text-[10px] text-muted-foreground block">
                    {voiceState === "listening"
                      ? "Listening..."
                      : voiceState === "thinking"
                      ? "Processing..."
                      : voiceState === "speaking"
                      ? "Pakka speaking"
                      : "Space to Talk"}
                  </span>
                </div>
              </div>

              {/* Optional Typed Text Input */}
              {showTypedInput && (
                <form onSubmit={handleTypedSubmit} className="flex gap-2 pt-1 border-t border-border">
                  <Input
                    value={typedText}
                    onChange={(e) => setTypedText(e.target.value)}
                    placeholder="Type Hinglish message (e.g. 'Geyser mein current aa raha hai')..."
                    className="h-10 text-xs"
                    disabled={voiceState === "thinking" || isTerminal}
                  />
                  <Button
                    type="submit"
                    size="sm"
                    className="h-10 px-3 shrink-0"
                    disabled={!typedText.trim() || voiceState === "thinking" || isTerminal}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: FSM State & Extracted Slots Inspector */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {/* FSM Dialogue Stepper */}
          <Card className="p-4 border-border bg-surface">
            <div className="flex items-center justify-between border-b border-border pb-2.5 mb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                <h3 className="font-bold text-sm text-foreground">Dialogue State</h3>
              </div>
              <Badge variant="outline" className="font-mono text-xs font-bold text-primary">
                {currentState}
              </Badge>
            </div>

            {/* Stepper Progress */}
            <div className="space-y-2">
              {flow === "booking" ? (
                [
                  { key: "ASK_PROBLEM", label: "Problem Identification" },
                  { key: "ASK_ADDRESS", label: "Delhi NCR Address" },
                  { key: "ASK_SLOT", label: "Preferred Time Slot" },
                  { key: "QUOTE", label: "Visiting Fee Quote" },
                  { key: "CONFIRM_READBACK", label: "Confirmation Readback" },
                  { key: "BOOKED", label: "Job Booked (PakkaStamp)" },
                ].map((step, idx) => {
                  const isCurrent = currentState === step.key;
                  const isPassed =
                    (step.key === "ASK_PROBLEM" && (slots.problem || slots.problem_key)) ||
                    (step.key === "ASK_ADDRESS" && slots.landmark_address) ||
                    (step.key === "ASK_SLOT" && slots.time_slot) ||
                    (step.key === "BOOKED" && isBooked);

                  return (
                    <div
                      key={step.key}
                      className={cn(
                        "flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg transition-colors",
                        isCurrent
                          ? "bg-primary/10 text-primary font-bold border border-primary/20"
                          : isPassed
                          ? "text-muted-foreground/90 font-medium"
                          : "text-muted-foreground/50"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] w-4">{idx + 1}.</span>
                        <span>{step.label}</span>
                      </div>
                      {isPassed && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />}
                    </div>
                  );
                })
              ) : (
                [
                  { key: "GREETING", label: "Identity Confirmation" },
                  { key: "CAPTURE_DATE", label: "Balance & Promise Date" },
                  { key: "TERMINAL", label: "Agreement / Escalation" },
                ].map((step, idx) => (
                  <div
                    key={step.key}
                    className={cn(
                      "flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg",
                      currentState === step.key
                        ? "bg-primary/10 text-primary font-bold border border-primary/20"
                        : "text-muted-foreground/60"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] w-4">{idx + 1}.</span>
                      <span>{step.label}</span>
                    </div>
                    {isTerminal && step.key === "TERMINAL" && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                    )}
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* Extracted Slots Card */}
          <Card className="p-4 border-border bg-surface relative overflow-hidden">
            <div className="flex items-center justify-between border-b border-border pb-2.5 mb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                <h3 className="font-bold text-sm text-foreground">Extracted Slots</h3>
              </div>
              <span className="text-[11px] font-mono text-muted-foreground">Rule-based FSM</span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Problem:</span>
                <span className="font-semibold text-foreground font-mono">
                  {slots.problem || slots.problem_key || "—"}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Address / Area:</span>
                <span className="font-semibold text-foreground font-mono">
                  {slots.landmark_address || "—"}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Time Slot:</span>
                <span className="font-semibold text-foreground font-mono">
                  {slots.time_slot || "—"}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Price Quote:</span>
                <span className="font-semibold text-emerald-600 font-mono">
                  {slots.price_estimate || "—"}
                </span>
              </div>

              {flow === "collection" && (
                <>
                  <div className="flex justify-between items-center py-1 border-b border-border/40">
                    <span className="text-muted-foreground">PTP Date:</span>
                    <span className="font-semibold text-primary font-mono">
                      {slots.ptp_date || "—"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-border/40">
                    <span className="text-muted-foreground">Disposition:</span>
                    <span className="font-semibold text-foreground font-mono">
                      {slots.disposition || "—"}
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Pakka Stamp when Job Booked */}
            {isBooked && (
              <div className="mt-4 pt-3 flex flex-col items-center justify-center animate-in fade-in zoom-in duration-300">
                <PakkaStamp visible={true} size="md" variant="success" />
                <p className="text-[11px] font-mono text-muted-foreground mt-2 text-center">
                  Job created & assigned to technician queue.
                </p>
              </div>
            )}
          </Card>

          {/* Quick Prompts Helper */}
          <Card className="p-3.5 border-border bg-surface-2/40 text-xs space-y-2">
            <span className="font-semibold text-foreground block text-[11px] uppercase tracking-wider">
              Try saying or typing:
            </span>
            <div className="space-y-1.5 font-mono text-[11px] text-muted-foreground">
              <button
                type="button"
                onClick={() => setTypedText("Mera geyser se paani tapak raha hai neeche se")}
                className="w-full text-left p-1.5 rounded hover:bg-surface border border-transparent hover:border-border transition-colors truncate block"
              >
                👉 &quot;Mera geyser se paani tapak raha hai&quot;
              </button>
              <button
                type="button"
                onClick={() => setTypedText("Mayur Vihar Phase 1 pocket 2")}
                className="w-full text-left p-1.5 rounded hover:bg-surface border border-transparent hover:border-border transition-colors truncate block"
              >
                👉 &quot;Mayur Vihar Phase 1 Pocket 2&quot;
              </button>
              <button
                type="button"
                onClick={() => setTypedText("Geyser mein current aa raha hai shock lag raha")}
                className="w-full text-left p-1.5 rounded hover:bg-surface border border-transparent hover:border-border transition-colors truncate block text-destructive"
              >
                ⚡ &quot;Geyser mein current aa raha hai&quot;
              </button>
              <button
                type="button"
                onClick={() => setTypedText("Kya tum robot ho ya asli insaan?")}
                className="w-full text-left p-1.5 rounded hover:bg-surface border border-transparent hover:border-border transition-colors truncate block"
              >
                🤖 &quot;Kya tum robot ho ya asli insaan?&quot;
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
