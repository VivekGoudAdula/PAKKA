import { create } from "zustand";

export interface DemoBeat {
  id: number;
  name: string;
  shortLabel: string;
  description: string;
  route: string;
}

export const DEMO_BEATS: DemoBeat[] = [
  {
    id: 1,
    name: "Customer Call",
    shortLabel: "Inbound Call",
    description: "Caller reports geyser heating breakdown in Hinglish",
    route: "/app/live?beat=1",
  },
  {
    id: 2,
    name: "Booking Confirmed",
    shortLabel: "Hinglish Booking",
    description: "Slots extracted, visiting fee quoted, PakkaStamp issued",
    route: "/app/live?beat=2",
  },
  {
    id: 3,
    name: "Auto-Dispatch",
    shortLabel: "Tech Matching",
    description: "Ranks technician by geyser specialty and current workload",
    route: "/app/live?beat=3",
  },
  {
    id: 4,
    name: "Tech Acceptance",
    shortLabel: "Voice Dispatch",
    description: "Outbound call to Imtiaz Ali with instant verbal acceptance",
    route: "/app/live?beat=4",
  },
  {
    id: 5,
    name: "Payment Collection",
    shortLabel: "Tone Ladder",
    description: "Automated polite payment recovery call with PTP date capture",
    route: "/app/payments?beat=5",
  },
];

interface DemoDirectorState {
  currentBeat: number;
  isPlaying: boolean;
  recordingMode: boolean;
  setBeat: (beat: number) => void;
  nextBeat: () => void;
  prevBeat: () => void;
  setIsPlaying: (playing: boolean) => void;
  togglePlay: () => void;
  toggleRecordingMode: () => void;
  resetDemo: () => void;
}

export const useDemoDirectorStore = create<DemoDirectorState>((set, get) => ({
  currentBeat: 1,
  isPlaying: false,
  recordingMode: false,
  setBeat: (beat: number) => set({ currentBeat: Math.min(Math.max(beat, 1), 5) }),
  nextBeat: () => {
    const { currentBeat } = get();
    if (currentBeat < 5) {
      set({ currentBeat: currentBeat + 1 });
    } else {
      set({ isPlaying: false });
    }
  },
  prevBeat: () => {
    const { currentBeat } = get();
    if (currentBeat > 1) {
      set({ currentBeat: currentBeat - 1 });
    }
  },
  setIsPlaying: (isPlaying: boolean) => set({ isPlaying }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  toggleRecordingMode: () => set((state) => ({ recordingMode: !state.recordingMode })),
  resetDemo: () => set({ currentBeat: 1, isPlaying: false }),
}));

