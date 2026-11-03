/**
 * Core domain types for the Pakka dashboard and voice assistant.
 * All seed data and future API responses follow this schema.
 */

export type CallStatus = "booked" | "needs_human" | "missed" | "in_progress";

export interface TranscriptMessage {
  id: string;
  role: "caller" | "bot";
  text: string;
  timestamp: string;
  is_disclosure?: boolean;
}

export interface ExtractedSlots {
  problem?: string;
  landmark_address?: string;
  time_slot?: string;
  price_range_min?: number;
  price_range_max?: number;
  customer_name?: string;
}

export interface Call {
  id: string;
  caller_number: string;
  caller_number_masked: string;
  customer_name?: string;
  timestamp: string;
  status: CallStatus;
  duration_seconds: number;
  summary: string;
  recording_url?: string;
  extracted_slots: ExtractedSlots;
  transcript: TranscriptMessage[];
}

export type JobStatus = "new" | "booked" | "dispatched" | "done" | "paid";

export interface Job {
  id: string;
  call_id: string;
  title: string;
  problem: string;
  landmark_address: string;
  time_slot: string;
  price_estimate: string;
  price_min: number;
  price_max: number;
  status: JobStatus;
  technician_id?: string;
  technician_name?: string;
  technician_avatar?: string;
  confirmed_at?: string;
  customer_name: string;
  customer_phone_masked: string;
}

export type TechnicianStatus = "available" | "on_job" | "off_duty";

export interface Technician {
  id: string;
  name: string;
  phone_masked: string;
  avatar: string;
  trade: string;
  status: TechnicianStatus;
  last_voice_confirmation: string;
  last_confirmation_time: string;
  accept_rate: number;
  total_jobs: number;
  active_job_id?: string;
}

export type PromiseStatus = "pending" | "due_today" | "broken" | "paid";

export interface ReminderEvent {
  id: string;
  timestamp: string;
  type: "voice_call" | "sms" | "promise_made" | "payment_received" | "dispute_raised";
  note: string;
  outcome?: string;
}

export interface PaymentPromise {
  id: string;
  customer_id: string;
  customer_name: string;
  customer_phone_masked: string;
  job_id: string;
  job_title: string;
  amount: number;
  due_date: string; // ISO date string (YYYY-MM-DD)
  base_due_days_offset: number; // For clock store relative calculation
  status: PromiseStatus;
  notes?: string;
  reminder_trail: ReminderEvent[];
}

export interface PriceItem {
  id: string;
  service_name: string;
  category: "Geyser" | "Plumbing" | "Motor" | "Drainage" | "General";
  min_price: number;
  max_price: number;
  unit: string;
}

export interface OverviewStats {
  calls_answered: number;
  jobs_booked: number;
  rupees_pending: number;
  rupees_collected: number;
  active_call?: {
    call_id: string;
    caller_masked: string;
    started_at: string;
    state: string;
  };
}
