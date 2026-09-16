from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from finance_app.analytics.metrics import AllocationItem, allocation_by, concentration_hhi, project_compound, weighted_expected_return
from finance_app.db import Database
from finance_app.models.entities import AccountSnapshot, AssetPosition, FinancialAccount, HouseholdMember, MonthlyBudget, NetWorthSnapshot, Transaction
from finance_app.security.crypto import CryptoService


class FinanceService:
    """Application service for financial data and household permissions."""

    def __init__(self, database: Database, crypto: CryptoService) -> None:
        self._database = database
        self._crypto = crypto

    def household_for_user(self, user_id: int) -> tuple[int, str, str, bool]:
        with self._database.session() as session:
            membership = session.scalar(select(HouseholdMember).where(HouseholdMember.user_id == user_id))
            if not membership:
                raise ValueError("Aucun foyer associé à cet utilisateur.")
            return membership.household_id, membership.household.name, membership.role, membership.can_view_household

    def add_account(self, user_id: int, name: str, kind: str, balance: Decimal, *, shared: bool, is_liability: bool = False, institution: str = "", notes: str = "") -> int:
        household_id, _, _, _ = self.household_for_user(user_id)
        if not name.strip():
            raise ValueError("Le nom du compte est obligatoire.")
        with self._database.session() as session:
            account = FinancialAccount(
                owner_user_id=None if shared else user_id,
                household_id=household_id if shared else None,
                name_encrypted=self._crypto.encrypt(name.strip()),
                institution_encrypted=self._crypto.encrypt(institution.strip()),
                notes_encrypted=self._crypto.encrypt(notes.strip()),
                kind=kind,
                current_balance=balance,
                is_liability=is_liability,
            )
            session.add(account)
            session.flush()
            session.add(AccountSnapshot(account_id=account.id, captured_on=date.today(), balance=balance))
            return account.id

    def _visible_accounts(self, session, user_id: int) -> list[FinancialAccount]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        personal = session.scalars(select(FinancialAccount).where(FinancialAccount.owner_user_id == user_id, FinancialAccount.is_archived.is_(False))).all()
        if not can_view:
            return list(personal)
        shared = session.scalars(select(FinancialAccount).where(FinancialAccount.household_id == household_id, FinancialAccount.is_archived.is_(False))).all()
        return list({account.id: account for account in [*personal, *shared]}.values())

    def list_accounts(self, user_id: int) -> list[dict[str, object]]:
        with self._database.session() as session:
            return [self._account_dict(account) for account in self._visible_accounts(session, user_id)]

    def _account_dict(self, account: FinancialAccount) -> dict[str, object]:
        return {
            "id": account.id,
            "name": self._crypto.decrypt(account.name_encrypted),
            "institution": self._crypto.decrypt(account.institution_encrypted),
            "notes": self._crypto.decrypt(account.notes_encrypted),
            "kind": account.kind,
            "balance": Decimal(account.current_balance),
            "liability": account.is_liability,
            "shared": account.household_id is not None,
            "created_at": account.created_at,
        }

    def _can_manage_account(self, session, user_id: int, account: FinancialAccount) -> bool:
        household_id, _, role, _ = self.household_for_user(user_id)
        return account.owner_user_id == user_id or (account.household_id == household_id and role == "admin_foyer")

    def update_account(self, user_id: int, account_id: int, *, name: str, kind: str, institution: str, notes: str, balance: Decimal) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
            if not name.strip():
                raise ValueError("Le nom du compte est obligatoire.")
            old_balance = Decimal(account.current_balance)
            account.name_encrypted = self._crypto.encrypt(name.strip())
            account.institution_encrypted = self._crypto.encrypt(institution.strip())
            account.notes_encrypted = self._crypto.encrypt(notes.strip())
            account.kind = kind
            account.current_balance = balance
            if balance != old_balance:
                session.add(AccountSnapshot(account_id=account.id, captured_on=date.today(), balance=balance))

    def delete_account(self, user_id: int, account_id: int) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
            session.delete(account)

    def archive_account(self, user_id: int, account_id: int) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
            account.is_archived = True

    def account_history(self, user_id: int, account_id: int) -> list[dict[str, object]]:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or account not in self._visible_accounts(session, user_id):
                raise PermissionError("Compte non accessible.")
            snapshots = session.scalars(select(AccountSnapshot).where(AccountSnapshot.account_id == account_id).order_by(AccountSnapshot.captured_on.asc(), AccountSnapshot.id.asc())).all()
            return [{"date": item.captured_on, "balance": Decimal(item.balance)} for item in snapshots]

    def add_transaction(self, account_id: int, booked_on: date, category: str, label: str, amount: Decimal, *, is_shared: bool) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None:
                raise ValueError("Compte introuvable.")
            account.current_balance = Decimal(account.current_balance) + amount
            session.add(Transaction(account_id=account_id, booked_on=booked_on, category=category.strip() or "Autre", label_encrypted=self._crypto.encrypt(label.strip()), amount=amount, is_shared=is_shared))
            session.add(AccountSnapshot(account_id=account_id, captured_on=booked_on, balance=account.current_balance))

    def update_transaction(self, user_id: int, transaction_id: int, *, amount: Decimal, category: str, label: str) -> None:
        with self._database.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                raise ValueError("Transaction introuvable.")
            account = session.get(FinancialAccount, transaction.account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur cette transaction.")
            account.current_balance = Decimal(account.current_balance) - Decimal(transaction.amount) + amount
            transaction.amount, transaction.category, transaction.label_encrypted = amount, category.strip() or "Autre", self._crypto.encrypt(label.strip())
            session.add(AccountSnapshot(account_id=account.id, captured_on=date.today(), balance=account.current_balance))

    def delete_transaction(self, user_id: int, transaction_id: int) -> None:
        with self._database.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                return
            account = session.get(FinancialAccount, transaction.account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur cette transaction.")
            account.current_balance = Decimal(account.current_balance) - Decimal(transaction.amount)
            session.delete(transaction)
            session.add(AccountSnapshot(account_id=account.id, captured_on=date.today(), balance=account.current_balance))

    def add_asset(self, account_id: int, label: str, asset_kind: str, value: Decimal, sector: str, geography: str, expected_return: Decimal) -> None:
        with self._database.session() as session:
            if session.get(FinancialAccount, account_id) is None:
                raise ValueError("Compte introuvable.")
            session.add(AssetPosition(account_id=account_id, label_encrypted=self._crypto.encrypt(label.strip()), asset_kind=asset_kind, value=value, sector=sector.strip() or "Non renseigné", geography=geography.strip() or "Non renseigné", expected_annual_return=expected_return))

    def record_snapshot(self, user_id: int) -> None:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return
        totals = self._calculate_totals(user_id)
        with self._database.session() as session:
            if not session.scalar(select(NetWorthSnapshot).where(NetWorthSnapshot.household_id == household_id, NetWorthSnapshot.captured_on == date.today())):
                session.add(NetWorthSnapshot(household_id=household_id, captured_on=date.today(), gross_assets=totals["gross"], liabilities=totals["liabilities"], net_worth=totals["net"]))

    def net_worth_history(self, user_id: int) -> list[dict[str, object]]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return []
        with self._database.session() as session:
            rows = session.scalars(select(NetWorthSnapshot).where(NetWorthSnapshot.household_id == household_id).order_by(NetWorthSnapshot.captured_on.asc())).all()
            return [{"date": row.captured_on, "gross": Decimal(row.gross_assets), "liabilities": Decimal(row.liabilities), "net": Decimal(row.net_worth)} for row in rows]

    def _calculate_totals(self, user_id: int) -> dict[str, Decimal]:
        accounts = self.list_accounts(user_id)
        gross = sum((row["balance"] for row in accounts if not row["liability"]), Decimal("0"))
        liabilities = sum((abs(row["balance"]) for row in accounts if row["liability"]), Decimal("0"))
        return {"gross": gross, "liabilities": liabilities, "net": gross - liabilities}

    def dashboard(self, user_id: int) -> dict[str, object]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        account_rows = self.list_accounts(user_id)
        totals = self._calculate_totals(user_id)
        account_ids = [int(row["id"]) for row in account_rows]
        with self._database.session() as session:
            assets = session.scalars(select(AssetPosition).where(AssetPosition.account_id.in_(account_ids))).all() if account_ids else []
            transactions = session.scalars(select(Transaction).where(Transaction.account_id.in_(account_ids)).order_by(Transaction.booked_on.desc(), Transaction.id.desc())).all() if account_ids else []
            expenses: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
            for tx in transactions:
                if Decimal(tx.amount) < 0: expenses[tx.category] += abs(Decimal(tx.amount))
            by_type = allocation_by((a.asset_kind, Decimal(a.value)) for a in assets)
            by_sector = allocation_by((a.sector, Decimal(a.value)) for a in assets)
            by_geography = allocation_by((a.geography, Decimal(a.value)) for a in assets)
            expected = weighted_expected_return(AllocationItem(a.asset_kind, Decimal(a.value), Decimal(a.expected_annual_return)) for a in assets)
            forecast = project_compound(max(totals["net"], Decimal("0")), expected, years=10)
            first_of_month = date.today().replace(day=1)
            budgets = session.scalars(select(MonthlyBudget).where(MonthlyBudget.household_id == household_id, MonthlyBudget.month == first_of_month)).all() if can_view else []
        planned = sum((Decimal(b.planned_amount) for b in budgets), Decimal("0"))
        return {**totals, "expenses": dict(sorted(expenses.items(), key=lambda item: item[1], reverse=True)), "allocation_type": by_type, "allocation_sector": by_sector, "allocation_geography": by_geography, "hhi": concentration_hhi([Decimal(a.value) for a in assets]), "expected_return": expected, "forecast": forecast, "budget_planned": planned, "budget_spent": sum(expenses.values(), Decimal("0")), "accounts": account_rows, "transaction_count": len(transactions)}

    def set_budget(self, user_id: int, category: str, amount: Decimal) -> None:
        household_id, _, role, _ = self.household_for_user(user_id)
        if role != "admin_foyer":
            raise PermissionError("Seul l'admin_foyer peut modifier le budget du foyer.")
        month = date.today().replace(day=1)
        with self._database.session() as session:
            item = session.scalar(select(MonthlyBudget).where(MonthlyBudget.household_id == household_id, MonthlyBudget.month == month, MonthlyBudget.category == category))
            if item: item.planned_amount = amount
            else: session.add(MonthlyBudget(household_id=household_id, month=month, category=category, planned_amount=amount))
