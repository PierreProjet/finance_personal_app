from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ImportedTransaction:
    """Normalized transaction produced by any banking connector."""

    booked_on: date
    label: str
    amount: Decimal
    category: str = "Autre"
    external_id: str | None = None


class BankingConnector(Protocol):
    """Future-proof boundary for bank aggregators and direct bank APIs."""

    provider_name: str

    def import_transactions(self, account_reference: str) -> list[ImportedTransaction]:
        """Return normalized transactions for a linked account."""
        ...


class ManualImportConnector:
    """Connector used by the MVP: data comes from local CSV import."""

    provider_name = "manual"

    def __init__(self, transactions: list[ImportedTransaction]) -> None:
        self._transactions = transactions

    def import_transactions(self, account_reference: str) -> list[ImportedTransaction]:
        """Return already validated local transactions; no network is used."""
        return list(self._transactions)


# A production aggregator can implement BankingConnector without changing
# the domain or UI. Credentials and OAuth tokens must never be stored in Git.
