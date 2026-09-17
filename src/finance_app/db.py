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
        Base.metadata.create_all(self.engine)

    def _upgrade_legacy_schema(self) -> None:
        """Apply small idempotent upgrades required by pre-migration MVP databases."""
        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        if "financial_accounts" in tables:
            columns = {
                column["name"]
                for column in inspector.get_columns("financial_accounts")
            }
            upgrades = []
            additions = {
                "notes_encrypted": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "notes_encrypted VARCHAR(2000) DEFAULT ''"
                ),
                "is_archived": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "is_archived BOOLEAN DEFAULT 0"
                ),
                "details_encrypted": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "details_encrypted VARCHAR(4000) DEFAULT ''"
                ),
                "opened_on": (
                    "ALTER TABLE financial_accounts ADD COLUMN opened_on DATE"
                ),
                "annual_fee_percent": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "annual_fee_percent NUMERIC(8, 4) DEFAULT 0"
                ),
                "annual_fee_fixed": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "annual_fee_fixed NUMERIC(18, 2) DEFAULT 0"
                ),
                "availability_days": (
                    "ALTER TABLE financial_accounts ADD COLUMN "
                    "availability_days INTEGER DEFAULT 0"
                ),
            }
            for name, statement in additions.items():
                if name not in columns:
                    upgrades.append(statement)
            self._execute_upgrades(upgrades)

        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        if "account_snapshots" in tables:
            columns = {
                column["name"]
                for column in inspector.get_columns("account_snapshots")
            }
            upgrades = []
            if "source" not in columns:
                upgrades.append(
                    "ALTER TABLE account_snapshots ADD COLUMN "
                    "source VARCHAR(30) DEFAULT 'system'"
                )
            if "note_encrypted" not in columns:
                upgrades.append(
                    "ALTER TABLE account_snapshots ADD COLUMN "
                    "note_encrypted VARCHAR(1000) DEFAULT ''"
                )
            self._execute_upgrades(upgrades)

    def _execute_upgrades(self, statements: list[str]) -> None:
        if not statements:
            return
        with self.engine.begin() as connection:
            for statement in statements:
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
