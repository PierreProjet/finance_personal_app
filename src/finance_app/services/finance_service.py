from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from finance_app.analytics.metrics import (
    AllocationItem,
    allocation_by,
    concentration_hhi,
    project_compound,
    weighted_expected_return,
)
from finance_app.db import Database
from finance_app.models.entities import (
    AssetPosition,
    FinancialAccount,
    HouseholdMember,
    MonthlyBudget,
    Transaction,
)
from finance_app.security.crypto import CryptoService


class FinanceService:
    def __init__(self, database: Database, crypto: CryptoService) -> None:
        self._database = database
        self._crypto = crypto

    def household_for_user(self, user_id: int) -> tuple[int, str, str, bool]:
        with self._database.session() as session:
            membership = session.scalar(
                select(HouseholdMember).where(HouseholdMember.user_id == user_id)
            )
            if not membership:
                raise ValueError("Aucun foyer associé à cet utilisateur.")
            return (
                membership.household_id,
                membership.household.name,
                membership.role,
                membership.can_view_household,
            )

    def add_account(
        self,
        user_id: int,
        name: str,
        kind: str,
        balance: Decimal,
        *,
        shared: bool,
        is_liability: bool = False,
        institution: str = "",
    ) -> None:
        household_id, _, _, _ = self.household_for_user(user_id)
        with self._database.session() as session:
            session.add(
                FinancialAccount(
                    owner_user_id=None if shared else user_id,
                    household_id=household_id if shared else None,
                    name_encrypted=self._crypto.encrypt(name.strip()),
                    institution_encrypted=self._crypto.encrypt(institution.strip()),
                    kind=kind,
                    current_balance=balance,
                    is_liability=is_liability,
                )
            )

    def list_accounts(self, user_id: int) -> list[dict[str, object]]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        with self._database.session() as session:
            conditions = [FinancialAccount.owner_user_id == user_id]
            if can_view:
                conditions.append(FinancialAccount.household_id == household_id)
            accounts = session.scalars(select(FinancialAccount).where(*([] if False else [conditions[0]]))).all()
            # SQLite-friendly explicit merge avoids complex OR composition and keeps permissions obvious.
            if can_view:
                shared = session.scalars(
                    select(FinancialAccount).where(FinancialAccount.household_id == household_id)
                ).all()
                by_id = {account.id: account for account in [*accounts, *shared]}
                accounts = list(by_id.values())
            return [
                {
                    "id": account.id,
                    "name": self._crypto.decrypt(account.name_encrypted),
                    "kind": account.kind,
                    "balance": Decimal(account.current_balance),
                    "liability": account.is_liability,
                    "shared": account.household_id is not None,
                }
                for account in accounts
            ]

    def add_transaction(
        self,
        account_id: int,
        booked_on: date,
        category: str,
        label: str,
        amount: Decimal,
        *,
        is_shared: bool,
    ) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None:
                raise ValueError("Compte introuvable.")
            account.current_balance = Decimal(account.current_balance) + amount
            session.add(
                Transaction(
                    account_id=account_id,
                    booked_on=booked_on,
                    category=category.strip() or "Autre",
                    label_encrypted=self._crypto.encrypt(label.strip()),
                    amount=amount,
                    is_shared=is_shared,
                )
            )

    def add_asset(
        self,
        account_id: int,
        label: str,
        asset_kind: str,
        value: Decimal,
        sector: str,
        geography: str,
        expected_return: Decimal,
    ) -> None:
        with self._database.session() as session:
            session.add(
                AssetPosition(
                    account_id=account_id,
                    label_encrypted=self._crypto.encrypt(label.strip()),
                    asset_kind=asset_kind,
                    value=value,
                    sector=sector.strip() or "Non renseigné",
                    geography=geography.strip() or "Non renseigné",
                    expected_annual_return=expected_return,
                )
            )

    def dashboard(self, user_id: int) -> dict[str, object]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        account_rows = self.list_accounts(user_id)
        gross = sum((row["balance"] for row in account_rows if not row["liability"]), Decimal("0"))
        liabilities = sum((abs(row["balance"]) for row in account_rows if row["liability"]), Decimal("0"))
        net = gross - liabilities

        account_ids = [int(row["id"]) for row in account_rows]
        with self._database.session() as session:
            assets = []
            transactions = []
            if account_ids:
                assets = session.scalars(
                    select(AssetPosition).where(AssetPosition.account_id.in_(account_ids))
                ).all()
                transactions = session.scalars(
                    select(Transaction)
                    .where(Transaction.account_id.in_(account_ids))
                    .order_by(Transaction.booked_on.desc())
                ).all()

            expense_categories: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
            for tx in transactions:
                amount = Decimal(tx.amount)
                if amount < 0:
                    expense_categories[tx.category] += abs(amount)

            asset_values = [Decimal(a.value) for a in assets]
            by_type = allocation_by((a.asset_kind, Decimal(a.value)) for a in assets)
            by_sector = allocation_by((a.sector, Decimal(a.value)) for a in assets)
            by_geography = allocation_by((a.geography, Decimal(a.value)) for a in assets)
            expected = weighted_expected_return(
                AllocationItem(a.asset_kind, Decimal(a.value), Decimal(a.expected_annual_return))
                for a in assets
            )
            forecast = project_compound(max(net, Decimal("0")), expected, years=10)

            first_of_month = date.today().replace(day=1)
            budgets = session.scalars(
                select(MonthlyBudget).where(
                    MonthlyBudget.household_id == household_id,
                    MonthlyBudget.month == first_of_month,
                )
            ).all() if can_view else []

        planned = sum((Decimal(b.planned_amount) for b in budgets), Decimal("0"))
        spent = sum(expense_categories.values(), Decimal("0"))
        return {
            "gross": gross,
            "liabilities": liabilities,
            "net": net,
            "expenses": dict(sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)),
            "allocation_type": by_type,
            "allocation_sector": by_sector,
            "allocation_geography": by_geography,
            "hhi": concentration_hhi(asset_values),
            "expected_return": expected,
            "forecast": forecast,
            "budget_planned": planned,
            "budget_spent": spent,
            "accounts": account_rows,
        }

    def set_budget(self, user_id: int, category: str, amount: Decimal) -> None:
        household_id, _, role, _ = self.household_for_user(user_id)
        if role != "admin_foyer":
            raise PermissionError("Seul l'admin_foyer peut modifier le budget du foyer.")
        month = date.today().replace(day=1)
        with self._database.session() as session:
            item = session.scalar(
                select(MonthlyBudget).where(
                    MonthlyBudget.household_id == household_id,
                    MonthlyBudget.month == month,
                    MonthlyBudget.category == category,
                )
            )
            if item:
                item.planned_amount = amount
            else:
                session.add(
                    MonthlyBudget(
                        household_id=household_id,
                        month=month,
                        category=category,
                        planned_amount=amount,
                    )
                )
