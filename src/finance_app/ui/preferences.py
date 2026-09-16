from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PREFERENCES = {
    "theme": "dark",
    "accent_color": "#6C63FF",
    "show_net_worth": True,
    "show_accounts": True,
    "show_budget": True,
    "show_analytics": True,
    "compact_mode": False,
}


class PreferencesStore:
    """Stores non-financial UI preferences locally, separately from financial data."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory / "preferences"
        self._directory.mkdir(parents=True, exist_ok=True)

    def load(self, user_id: int) -> dict[str, object]:
        path = self._directory / f"user_{user_id}.json"
        if not path.exists():
            return DEFAULT_PREFERENCES.copy()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return DEFAULT_PREFERENCES.copy()
        result = DEFAULT_PREFERENCES.copy()
        result.update({key: value for key, value in data.items() if key in result})
        return result

    def save(self, user_id: int, preferences: dict[str, object]) -> None:
        path = self._directory / f"user_{user_id}.json"
        safe_values = {key: preferences.get(key, default) for key, default in DEFAULT_PREFERENCES.items()}
        path.write_text(json.dumps(safe_values, indent=2, ensure_ascii=False), encoding="utf-8")
