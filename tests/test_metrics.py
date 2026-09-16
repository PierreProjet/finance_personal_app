from decimal import Decimal

from finance_app.analytics.metrics import (
    AllocationItem,
    concentration_hhi,
    net_worth,
    project_compound,
    weighted_expected_return,
)


def test_net_worth() -> None:
    gross, debt, net = net_worth([Decimal("100"), Decimal("50")], [Decimal("30")])
    assert (gross, debt, net) == (Decimal("150"), Decimal("30"), Decimal("120"))


def test_concentration_hhi_for_equal_positions() -> None:
    assert concentration_hhi([Decimal("50"), Decimal("50")]) == Decimal("0.50")


def test_weighted_return() -> None:
    value = weighted_expected_return(
        [
            AllocationItem("ETF", Decimal("75"), Decimal("0.08")),
            AllocationItem("Bond", Decimal("25"), Decimal("0.02")),
        ]
    )
    assert value == Decimal("0.065")


def test_forecast_has_requested_horizon() -> None:
    points = project_compound(Decimal("1000"), Decimal("0.05"), years=10)
    assert len(points) == 11
    assert points[-1].value > Decimal("1000")
