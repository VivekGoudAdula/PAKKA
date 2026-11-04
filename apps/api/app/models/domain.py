"""
Domain SQLModel database models for Pakka.
Matches schema across frontend and backend.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Customer(SQLModel, table=True):
    """Customer entity with phone and primary address."""

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    phone_masked: str
    phone_raw: str | None = None
    default_address: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Technician(SQLModel, table=True):
    """Service technician registered for voice dispatch."""

    id: str = Field(primary_key=True)
    name: str
    phone_masked: str
    phone: str | None = None
    avatar: str = "T"
    trade: str
    status: str = "available"  # available, on_job, off_duty
    last_voice_confirmation: str = ""
    last_confirmation_time: str = ""
    accept_rate: int = 85
    total_jobs: int = 0
    active_jobs_count: int = 0

    @property
    def specialty(self) -> str:
        return self.trade

    @property
    def is_active(self) -> bool:
        return self.status != "off_duty"


class PriceItem(SQLModel, table=True):
    """Service catalog rate card used for price quotes."""

    id: str = Field(primary_key=True)
    service_name: str
    category: str
    min_price: int
    max_price: int
    unit: str = "per service"


class Job(SQLModel, table=True):
    """Confirmed customer service job booked via voice assistant."""

    id: str = Field(primary_key=True)
    call_id: str = Field(index=True)
    title: str
    problem: str
    landmark_address: str
    time_slot: str
    price_estimate: str
    price_min: int
    price_max: int
    status: str = "booked"  # new, booked, dispatched, done, paid
    technician_id: str | None = None
    technician_name: str | None = None
    technician_avatar: str | None = None
    confirmed_at: str | None = None
    customer_name: str
    customer_phone_masked: str
    paid_amount: int = 0
    balance: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallRecord(SQLModel, table=True):
    """Voice call record storing metadata, transcript turns, and extracted slots."""

    id: str = Field(primary_key=True)
    caller_number: str
    caller_number_masked: str
    customer_name: str | None = None
    timestamp: str
    status: str = "booked"  # booked, needs_human, missed, in_progress
    duration_seconds: int = 0
    summary: str = ""
    extracted_slots_json: str = "{}"  # JSON serialized slots
    transcript_json: str = "[]"  # JSON serialized transcript messages
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessSettings(SQLModel, table=True):
    """Business owner configuration and telephony bounds."""

    id: str = Field(default="default", primary_key=True)
    business_name: str = "Sharma Plumbing & Geyser Care"
    handoff_phone: str = "+91 98765 43210"
    outbound_start: str = "09:00"
    outbound_end: str = "20:00"
    auto_stop_wrong_number: bool = True
    never_deny_ai: bool = True
    custom_areas_json: str = "[]"
    auto_dispatch: bool = False


class Promise(SQLModel, table=True):
    """Promise to Pay (PTP) tracking debtor commitments and collection states."""

    id: str = Field(primary_key=True)
    customer_id: str = Field(index=True)
    customer_name: str
    customer_phone_masked: str
    customer_phone_raw: str | None = None
    job_id: str | None = Field(default=None, index=True)
    amount: int
    due_date: str  # YYYY-MM-DD
    status: str = "pending"  # pending, due_today, kept, broken, disputed, cancelled
    tone_level: int = 1  # 1 (gentle), 2 (firm follow-up), 3 (owner escalation)
    attempts_count: int = 0
    last_attempt_at: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReminderEvent(SQLModel, table=True):
    """Audit log trail of all collection reminder interactions and outcomes."""

    id: str = Field(primary_key=True)
    promise_id: str = Field(index=True)
    customer_id: str = Field(index=True)
    timestamp: str  # ISO string or human formatted
    kind: str = "call"  # call, callback, note
    disposition: str = "PTP"  # PTP, PAID, DISPUTE, WRONG_NUMBER, CALLBACK, NO_ANSWER, REFUSED, NEEDS_OWNER
    snippet: str = ""
    tone_level: int = 1  # 1, 2, 3
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SuppressedNumber(SQLModel, table=True):
    """Numbers permanently excluded from automated outbound calls (e.g. wrong number)."""

    id: str = Field(primary_key=True)
    phone_raw: str = Field(index=True, unique=True)
    reason: str = "wrong_number"  # wrong_number, opt_out, owner_flagged
    suppressed_at: datetime = Field(default_factory=datetime.utcnow)
