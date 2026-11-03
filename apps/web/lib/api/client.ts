import { Call, Job, PaymentPromise, PriceItem, PromiseStatus, Technician } from "../types";
import {
  SEED_CALLS,
  SEED_JOBS,
  SEED_PRICE_LIST,
  SEED_PROMISES,
  SEED_TECHNICIANS,
} from "./seed-data";

/**
 * Compute dynamic promise status based on the clock store's days offset.
 * Example:
 * - base offset +1 (due tomorrow) with daysOffset = +1 -> due_today
 * - base offset +1 with daysOffset >= +2 -> broken
 */
export function computePromiseStatus(
  baseOffset: number,
  currentDaysOffset: number,
  originalStatus: PromiseStatus
): PromiseStatus {
  if (originalStatus === "paid") return "paid";
  const effectiveOffset = baseOffset - currentDaysOffset;
  if (effectiveOffset > 0) return "pending";
  if (effectiveOffset === 0) return "due_today";
  return "broken";
}

/** Simulate network delay for realistic query behavior */
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchOverviewStats(daysOffset: number = 0) {
  await delay(120);

  const activePromises = SEED_PROMISES.map((p) => ({
    ...p,
    computedStatus: computePromiseStatus(p.base_due_days_offset, daysOffset, p.status),
  }));

  const rupeesPending = activePromises
    .filter((p) => p.computedStatus !== "paid")
    .reduce((sum, p) => sum + p.amount, 0);

  const rupeesCollected = activePromises
    .filter((p) => p.computedStatus === "paid")
    .reduce((sum, p) => sum + p.amount, 0);

  return {
    calls_answered: SEED_CALLS.filter((c) => c.status !== "missed").length,
    jobs_booked: SEED_JOBS.length,
    rupees_pending: rupeesPending,
    rupees_collected: rupeesCollected,
    active_call: {
      call_id: "call_live_01",
      caller_masked: "+91 98XXXXXX88",
      started_at: "Just now",
      state: "Identifying problem: Geyser thermostat tripped",
    },
  };
}

export async function fetchCalls(filter: string = "all"): Promise<Call[]> {
  await delay(100);
  if (filter === "all") return SEED_CALLS;
  return SEED_CALLS.filter((c) => c.status === filter);
}

export async function fetchCallById(id: string): Promise<Call | undefined> {
  await delay(50);
  return SEED_CALLS.find((c) => c.id === id);
}

export async function fetchJobs(): Promise<Job[]> {
  await delay(100);
  return SEED_JOBS;
}

export async function fetchTechnicians(): Promise<Technician[]> {
  await delay(100);
  return SEED_TECHNICIANS;
}

export async function fetchPaymentPromises(daysOffset: number = 0): Promise<PaymentPromise[]> {
  await delay(100);
  return SEED_PROMISES.map((p) => ({
    ...p,
    status: computePromiseStatus(p.base_due_days_offset, daysOffset, p.status),
  }));
}

export async function fetchPriceList(): Promise<PriceItem[]> {
  await delay(80);
  return SEED_PRICE_LIST;
}
