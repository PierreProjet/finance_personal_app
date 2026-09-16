from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "FinanceFoyer"
APP_VERSION = "0.1.0"


def default_data_dir() -> Path:
    """Return a per-user application data directory without requiring admin rights."""
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    database_path: Path

    @classmethod
    def load(cls) -> Settings:
        data_dir = default_data_dir()
        return cls(data_dir=data_dir, database_path=data_dir / "finance.db")
