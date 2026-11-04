"""
Seed script to initialize SQLite database with synthetic records.
Consistent with the web seed data.
"""

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.domain import (
    BusinessSettings,
    Customer,
    Job,
    PriceItem,
    Promise,
    ReminderEvent,
    SuppressedNumber,
    Technician,
)

DEFAULT_PRICE_ITEMS = [
    PriceItem(
        id="price_01",
        service_name="Geyser Heating Coil Replacement",
        category="Geyser",
        min_price=450,
        max_price=750,
        unit="per coil + labour",
    ),
    PriceItem(
        id="price_02",
        service_name="Geyser Water Leakage Repair",
        category="Geyser",
        min_price=350,
        max_price=600,
        unit="per visit",
    ),
    PriceItem(
        id="price_03",
        service_name="Tap Leakage Repair / Washer Change",
        category="Plumbing",
        min_price=150,
        max_price=250,
        unit="per tap",
    ),
    PriceItem(
        id="price_04",
        service_name="Kitchen / Bathroom Drain Unblocking",
        category="Drainage",
        min_price=400,
        max_price=800,
        unit="per drain",
    ),
    PriceItem(
        id="price_05",
        service_name="Submersible Motor Inspection & Repair",
        category="Motor",
        min_price=500,
        max_price=1200,
        unit="inspection + repair",
    ),
    PriceItem(
        id="price_06",
        service_name="Pipe Burst Emergency Joint Repair",
        category="Plumbing",
        min_price=300,
        max_price=500,
        unit="per joint",
    ),
]

DEFAULT_TECHNICIANS = [
    Technician(
        id="tech_01",
        name="Vikash Kumar",
        phone_masked="+91 98XXXXXX41",
        avatar="VK",
        trade="Geyser & Electrical Specialist",
        status="available",
        last_voice_confirmation="haan, pakka, 2 baje pohoch jaunga",
        last_confirmation_time="10:15 AM",
        accept_rate=94,
        total_jobs=112,
    ),
    Technician(
        id="tech_02",
        name="Ramesh Kumar",
        phone_masked="+91 98XXXXXX42",
        avatar="RK",
        trade="Master Plumber & Pipe Expert",
        status="on_job",
        last_voice_confirmation="Haan main nikal raha hoon, aadhe ghante mein pahuchunga.",
        last_confirmation_time="09:45 AM",
        accept_rate=91,
        total_jobs=98,
    ),
    Technician(
        id="tech_03",
        name="Mohan Singh",
        phone_masked="+91 98XXXXXX43",
        avatar="MS",
        trade="Submersible Motor & Drain Expert",
        status="available",
        last_voice_confirmation="Ji sir, Chhatarpur kaam khatam ho gaya hai.",
        last_confirmation_time="Yesterday, 04:30 PM",
        accept_rate=88,
        total_jobs=76,
    ),
    Technician(
        id="tech_04",
        name="Dinesh Yadav",
        phone_masked="+91 98XXXXXX44",
        avatar="DY",
        trade="Sanitaryware & Fixture Specialist",
        status="off_duty",
        last_voice_confirmation="Aaj shaam ko available nahi hoon, kal subah bhej dena.",
        last_confirmation_time="02 Nov, 08:00 PM",
        accept_rate=79,
        total_jobs=59,
    ),
]

DEFAULT_PROMISES = [
    Promise(
        id="prom_01",
        customer_id="cust_01",
        customer_name="Harish Rawat",
        customer_phone_masked="+91 98XXXXXX05",
        customer_phone_raw="+919800000005",
        job_id="job_005",
        amount=450,
        due_date="2026-11-05",
        status="pending",
        tone_level=1,
    ),
    Promise(
        id="prom_02",
        customer_id="cust_02",
        customer_name="Vikram Sethi",
        customer_phone_masked="+91 98XXXXXX11",
        customer_phone_raw="+919800000011",
        job_id="job_009",
        amount=750,
        due_date="2026-11-04",
        status="due_today",
        tone_level=1,
    ),
    Promise(
        id="prom_03",
        customer_id="cust_03",
        customer_name="Karan Johar",
        customer_phone_masked="+91 98XXXXXX20",
        customer_phone_raw="+919800000020",
        job_id="job_014",
        amount=600,
        due_date="2026-11-02",
        status="broken",
        tone_level=2,
        attempts_count=2,
        last_attempt_at="2026-11-03T10:00:00",
    ),
    Promise(
        id="prom_04",
        customer_id="cust_04",
        customer_name="Manish Tiwari",
        customer_phone_masked="+91 98XXXXXX08",
        customer_phone_raw="+919800000008",
        job_id="job_007",
        amount=850,
        due_date="2026-11-02",
        status="kept",
        tone_level=1,
    ),
    Promise(
        id="prom_05",
        customer_id="cust_05",
        customer_name="Geeta Rao",
        customer_phone_masked="+91 98XXXXXX10",
        customer_phone_raw="+919800000010",
        job_id="job_008",
        amount=500,
        due_date="2026-11-03",
        status="disputed",
        tone_level=1,
    ),
]

DEFAULT_REMINDER_EVENTS = [
    ReminderEvent(
        id="rem_01",
        promise_id="prom_01",
        customer_id="cust_01",
        timestamp="03 Nov 05:15 PM",
        kind="call",
        disposition="PTP",
        snippet="Customer promised to pay by tomorrow morning.",
        tone_level=1,
    ),
    ReminderEvent(
        id="rem_02",
        promise_id="prom_02",
        customer_id="cust_02",
        timestamp="04 Nov 09:30 AM",
        kind="call",
        disposition="PTP",
        snippet="Customer promised to pay by 2:00 PM today.",
        tone_level=1,
    ),
    ReminderEvent(
        id="rem_03",
        promise_id="prom_03",
        customer_id="cust_03",
        timestamp="02 Nov 11:30 AM",
        kind="call",
        disposition="NO_ANSWER",
        snippet="Call rang 5 times, customer did not answer.",
        tone_level=2,
    ),
    ReminderEvent(
        id="rem_04",
        promise_id="prom_03",
        customer_id="cust_03",
        timestamp="03 Nov 10:00 AM",
        kind="call",
        disposition="REFUSED",
        snippet="Customer cut the call after hearing digital sahayak.",
        tone_level=2,
    ),
]


def seed_database() -> None:
    """Populate initial seed records if tables are empty."""
    init_db()
    with Session(engine) as session:
        # Check if settings exist
        settings_record = session.exec(select(BusinessSettings)).first()
        if not settings_record:
            session.add(BusinessSettings())

        # Check if price items exist
        existing_price = session.exec(select(PriceItem)).first()
        if not existing_price:
            for item in DEFAULT_PRICE_ITEMS:
                session.add(item)

        # Check if technicians exist
        existing_tech = session.exec(select(Technician)).first()
        if not existing_tech:
            for tech in DEFAULT_TECHNICIANS:
                session.add(tech)

        # Check if promises exist
        existing_promise = session.exec(select(Promise)).first()
        if not existing_promise:
            for prom in DEFAULT_PROMISES:
                session.add(prom)

        # Check if reminder events exist
        existing_rem = session.exec(select(ReminderEvent)).first()
        if not existing_rem:
            for rem in DEFAULT_REMINDER_EVENTS:
                session.add(rem)

        session.commit()


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully with initial records.")
