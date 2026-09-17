from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from math import pow


@dataclass(frozen=True, slots=True)
class AllocationItem:
    label: str
    value: Decimal
    expected_return: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    year: int
    value: Decimal


def net_worth(
    assets: Iterable[Decimal],
    liabilities: Iterable[Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    gross = sum(assets, Decimal("0"))
    debt = sum(liabilities, Decimal("0"))
    return gross, debt, gross - debt


def allocation_by(items: Iterable[tuple[str, Decimal]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for label, value in items:
        totals[label or "Non renseigné"] += value
    return dict(sorted(totals.items(), key=lambda pair: pair[1], reverse=True))


def concentration_hhi(items: Iterable[Decimal]) -> Decimal:
    values = [max(value, Decimal("0")) for value in items]
    total = sum(values, Decimal("0"))
    if total == 0:
        return Decimal("0")
    return sum((value / total) ** 2 for value in values)


def weighted_expected_return(items: Iterable[AllocationItem]) -> Decimal:
    positions = list(items)
    total = sum((p.value for p in positions), Decimal("0"))
    if total <= 0:
        return Decimal("0")
    return sum((p.value / total) * p.expected_return for p in positions)


def project_compound(
    starting_value: Decimal,
    annual_return: Decimal,
    annual_contribution: Decimal = Decimal("0"),
    years: int = 10,
) -> list[ForecastPoint]:
    """Create a transparent deterministic forecast; this is not investment advice."""
    if years < 0:
        raise ValueError("years doit être positif.")
    current = starting_value
    points = [ForecastPoint(year=0, value=current.quantize(Decimal("0.01")))]
    rate = float(annual_return)
    for year in range(1, years + 1):
        current = Decimal(str(float(current) * pow(1.0 + rate, 1))) + annual_contribution
        points.append(ForecastPoint(year=year, value=current.quantize(Decimal("0.01"))))
    return points
