"""
Database connection and session lifecycle for Pakka SQLite storage.
"""

import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "pakka.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def run_startup_migrations(target_engine: Any = None) -> None:
    """
    Idempotently migrates SQLite tables to match current SQLModel table schema.
    Inspects existing columns via PRAGMA table_info and adds missing columns
    using ALTER TABLE ... ADD COLUMN with safe defaults.
    """
    eng = target_engine or engine
    # Make sure all domain models are registered with SQLModel.metadata
    from app.models.domain import (  # noqa: F401
        BusinessSettings,
        CallRecord,
        Customer,
        Job,
        PriceItem,
        Promise,
        ReminderEvent,
        SuppressedNumber,
        Technician,
    )

    with eng.connect() as conn:
        for table_name, table in SQLModel.metadata.tables.items():
            res = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tname"),
                {"tname": table_name},
            ).fetchone()
            if not res:
                continue

            cols_info = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
            existing_col_names = {row[1] for row in cols_info}

            for col in table.columns:
                if col.name not in existing_col_names:
                    col_type = col.type.compile(dialect=eng.dialect)
                    default_clause = ""
                    if col.server_default is not None:
                        default_clause = f" DEFAULT {col.server_default.arg.text}"
                    elif col.default is not None and not callable(col.default.arg):
                        arg = col.default.arg
                        if isinstance(arg, bool):
                            default_clause = f" DEFAULT {1 if arg else 0}"
                        elif isinstance(arg, (int, float)):
                            default_clause = f" DEFAULT {arg}"
                        elif isinstance(arg, str):
                            default_clause = f" DEFAULT '{arg}'"
                    else:
                        type_str = str(col_type).upper()
                        if "INT" in type_str or "BOOL" in type_str:
                            default_clause = " DEFAULT 0"
                        elif "VARCHAR" in type_str or "TEXT" in type_str:
                            if col.name.endswith("_json"):
                                default_clause = " DEFAULT '[]'"
                            else:
                                default_clause = " DEFAULT ''"

                    alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"
                    logger.info("Running schema migration: %s", alter_stmt)
                    conn.execute(text(alter_stmt))
        conn.commit()


def init_db(target_engine: Any = None) -> None:
    """Create all tables in the SQLite database if not present and run column migrations."""
    eng = target_engine or engine
    SQLModel.metadata.create_all(eng)
    run_startup_migrations(eng)


def get_session() -> Generator[Session, None, None]:
    """Dependency for obtaining an active SQLModel database session."""
    with Session(engine) as session:
        yield session
