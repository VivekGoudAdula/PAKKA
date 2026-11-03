import { create } from "zustand";

interface ClockState {
  /** The base simulated date: Nov 3, 2026, 10:30 AM IST */
  baseDate: Date;
  /** Cumulative offset in hours */
  hoursOffset: number;
  /** Cumulative offset in days */
  daysOffset: number;
  /** Returns the current simulated Date */
  getCurrentTime: () => Date;
  /** Advance simulated time by N hours */
  advanceHours: (hours: number) => void;
  /** Advance simulated time by N days */
  advanceDays: (days: number) => void;
  /** Reset back to base simulation date */
  resetClock: () => void;
}

const INITIAL_DATE = new Date("2026-11-03T10:30:00");

export const useClockStore = create<ClockState>((set, get) => ({
  baseDate: INITIAL_DATE,
  hoursOffset: 0,
  daysOffset: 0,
  getCurrentTime: () => {
    const { baseDate, hoursOffset, daysOffset } = get();
    const current = new Date(baseDate.getTime());
    current.setHours(current.getHours() + hoursOffset);
    current.setDate(current.getDate() + daysOffset);
    return current;
  },
  advanceHours: (hours: number) =>
    set((state) => ({ hoursOffset: state.hoursOffset + hours })),
  advanceDays: (days: number) =>
    set((state) => ({ daysOffset: state.daysOffset + days })),
  resetClock: () => set({ hoursOffset: 0, daysOffset: 0 }),
}));
