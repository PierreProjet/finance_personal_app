from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from finance_app.models.entities import Base


def create_database_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path}", future=True)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


class Database:
    """Owns the local SQLite engine and applies backward-compatible schema changes."""

    def __init__(self, database_path: Path) -> None:
        self.engine = create_database_engine(database_path)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        self._upgrade_legacy_schema()

    def _upgrade_legacy_schema(self) -> None:
        """Apply small idempotent upgrades required by the early MVP versions."""
        inspector = inspect(self.engine)
        columns = {column["name"] for column in inspector.get_columns("financial_accounts")}
        upgrades = []
        if "notes_encrypted" not in columns:
            upgrades.append("ALTER TABLE financial_accounts ADD COLUMN notes_encrypted VARCHAR(2000) DEFAULT ''")
        if "is_archived" not in columns:
            upgrades.append("ALTER TABLE financial_accounts ADD COLUMN is_archived BOOLEAN DEFAULT 0")
        if upgrades:
            with self.engine.begin() as connection:
                for statement in upgrades:
                    connection.execute(text(statement))

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
