import { create } from "zustand";

interface ModeState {
  mode: "DEMO" | "LIVE";
  wsConnected: boolean;
  setMode: (mode: "DEMO" | "LIVE") => void;
  setWsConnected: (connected: boolean) => void;
}

export const useModeStore = create<ModeState>((set) => ({
  mode: "DEMO",
  wsConnected: false,
  setMode: (mode) => set({ mode }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
}));
