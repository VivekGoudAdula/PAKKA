"""
apps/api/tests/test_db_migration.py
Unit tests for idempotent SQLite startup migration of stale schemas.
Verifies that old SQLite databases missing columns (such as custom_areas_json)
are automatically migrated without data loss.
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, create_engine, select

from app.db import run_startup_migrations
from app.models.domain import BusinessSettings


def test_sqlite_startup_migration_old_schema(tmp_path: Path) -> None:
    """
    Simulates a stale database from previous phases where BusinessSettings
    lacked custom_areas_json and auto_dispatch. Verifies migration detects
    missing columns and applies ALTER TABLE ADD COLUMN.
    """
    db_file = tmp_path / "legacy_test.db"
    conn_raw = sqlite3.connect(str(db_file))
    cur = conn_raw.cursor()

    # Create old schema table missing custom_areas_json, auto_dispatch, owner_name
    cur.execute(
        """
        CREATE TABLE businesssettings (
            id VARCHAR NOT NULL PRIMARY KEY,
            business_name VARCHAR NOT NULL,
            handoff_phone VARCHAR NOT NULL,
            outbound_start VARCHAR NOT NULL,
            outbound_end VARCHAR NOT NULL,
            auto_stop_wrong_number INTEGER NOT NULL,
            never_deny_ai INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO businesssettings (
            id, business_name, handoff_phone, outbound_start, outbound_end,
            auto_stop_wrong_number, never_deny_ai
        ) VALUES (
            'default', 'Legacy Plumbing', '+91 98765 00000', '09:00', '20:00', 1, 1
        )
        """
    )
    conn_raw.commit()
    conn_raw.close()

    # Connect SQLModel engine to this legacy database
    test_engine = create_engine(f"sqlite:///{db_file}")

    # Before migration: querying custom_areas_json fails
    with pytest.raises(SQLAlchemyError), Session(test_engine) as session:
        session.exec(select(BusinessSettings)).first()

    # Run idempotent migration
    run_startup_migrations(test_engine)

    # After migration: querying BusinessSettings succeeds with defaults
    with Session(test_engine) as session:
        bs = session.exec(select(BusinessSettings)).first()
        assert bs is not None
        assert bs.id == "default"
        assert bs.business_name == "Legacy Plumbing"
        assert bs.custom_areas_json == "[]"
        assert bs.auto_dispatch is False
        assert bs.owner_name == "Ramesh Sharma"

    # Verify idempotency by running migration again
    run_startup_migrations(test_engine)
    with Session(test_engine) as session:
        bs_again = session.exec(select(BusinessSettings)).first()
        assert bs_again is not None
        assert bs_again.business_name == "Legacy Plumbing"

