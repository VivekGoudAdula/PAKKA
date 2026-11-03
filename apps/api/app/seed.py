"""
Seed script to initialize SQLite database with synthetic records.
Consistent with the web seed data.
"""

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.domain import (
    BusinessSettings,
    PriceItem,
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

        session.commit()


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully with initial records.")
