from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class MarketQuote:
    """Normalized market observation used by the application."""

    symbol: str
    observed_on: date
    close: Decimal
    currency: str
    source: str


class MarketDataProvider(Protocol):
    """Stable interface for free market-data providers."""

    provider_name: str

    def get_history(self, symbol: str, start: date, end: date) -> list[MarketQuote]:
        """Return historical observations for a symbol."""
        ...


class ManualMarketDataProvider:
    """Offline provider for tests and manual data entry."""

    provider_name = "manual"

    def __init__(self, quotes: list[MarketQuote]) -> None:
        self._quotes = quotes

    def get_history(self, symbol: str, start: date, end: date) -> list[MarketQuote]:
        """Filter locally supplied observations without making network calls."""
        return [
            quote
            for quote in self._quotes
            if quote.symbol == symbol and start <= quote.observed_on <= end
        ]
