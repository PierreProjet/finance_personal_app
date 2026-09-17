from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select

from finance_app.analytics.metrics import (
    AllocationItem,
    allocation_by,
    concentration_hhi,
    project_compound,
    weighted_expected_return,
)
from finance_app.db import Database
from finance_app.models.entities import (
    AccountSnapshot,
    AssetPosition,
    FinancialAccount,
    HouseholdMember,
    HouseholdProject,
    HouseholdProjectContribution,
    MonthlyBudget,
    NetWorthSnapshot,
    Transaction,
    User,
)
from finance_app.security.crypto import CryptoService


PROJECTION_MODELS: dict[str, Decimal] = {
    "prudent": Decimal("0.025"),
    "central": Decimal("0.045"),
    "dynamique": Decimal("0.065"),
}

INVESTMENT_PROFILES: dict[str, dict[str, int]] = {
    "prudent": {"actions": 25, "obligations": 45, "liquidites": 20, "immobilier": 10},
    "equilibre": {"actions": 50, "obligations": 25, "liquidites": 10, "immobilier": 15},
    "dynamique": {"actions": 75, "obligations": 10, "liquidites": 5, "immobilier": 10},
}


class FinanceService:
    """Application service for financial data and household permissions."""

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
        notes: str = "",
        opened_on: date | None = None,
        annual_fee_percent: Decimal = Decimal("0"),
        annual_fee_fixed: Decimal = Decimal("0"),
        availability_days: int = 0,
        details: dict[str, str] | None = None,
    ) -> int:
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
                details_encrypted=self._encrypt_details(details),
                kind=kind,
                opened_on=opened_on,
                annual_fee_percent=annual_fee_percent,
                annual_fee_fixed=annual_fee_fixed,
                availability_days=max(0, availability_days),
                current_balance=balance,
                is_liability=is_liability,
            )
            session.add(account)
            session.flush()
            session.add(
                AccountSnapshot(
                    account_id=account.id,
                    captured_on=date.today(),
                    balance=balance,
                    source="creation",
                    note_encrypted=self._crypto.encrypt("Solde initial"),
                )
            )
            return account.id

    def _encrypt_details(self, details: dict[str, str] | None) -> str:
        raw = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
        return self._crypto.encrypt(raw)

    def _decrypt_details(self, value: str) -> dict[str, str]:
        if not value:
            return {}
        try:
            data = json.loads(self._crypto.decrypt(value))
        except (ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(item) for key, item in data.items()}

    def _visible_accounts(self, session, user_id: int) -> list[FinancialAccount]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        conditions = [FinancialAccount.owner_user_id == user_id]
        if can_view:
            member_ids = session.scalars(
                select(HouseholdMember.user_id).where(
                    HouseholdMember.household_id == household_id
                )
            ).all()
            conditions = [
                FinancialAccount.owner_user_id.in_(member_ids),
                FinancialAccount.household_id == household_id,
            ]
        accounts = session.scalars(
            select(FinancialAccount).where(
                or_(*conditions),
                FinancialAccount.is_archived.is_(False),
            )
        ).all()
        return list({account.id: account for account in accounts}.values())

    def list_accounts(self, user_id: int) -> list[dict[str, object]]:
        with self._database.session() as session:
            accounts = self._visible_accounts(session, user_id)
            return [self._account_dict(account) for account in accounts]

    def _account_dict(self, account: FinancialAccount) -> dict[str, object]:
        return {
            "id": account.id,
            "name": self._crypto.decrypt(account.name_encrypted),
            "institution": self._crypto.decrypt(account.institution_encrypted),
            "notes": self._crypto.decrypt(account.notes_encrypted),
            "details": self._decrypt_details(account.details_encrypted),
            "kind": account.kind,
            "opened_on": account.opened_on,
            "annual_fee_percent": Decimal(account.annual_fee_percent),
            "annual_fee_fixed": Decimal(account.annual_fee_fixed),
            "availability_days": account.availability_days,
            "balance": Decimal(account.current_balance),
            "liability": account.is_liability,
            "shared": account.household_id is not None,
            "owner_user_id": account.owner_user_id,
            "created_at": account.created_at,
        }

    def _can_manage_account(self, session, user_id: int, account: FinancialAccount) -> bool:
        household_id, _, role, _ = self.household_for_user(user_id)
        return account.owner_user_id == user_id or (
            account.household_id == household_id and role == "admin_foyer"
        )

    def update_account(
        self,
        user_id: int,
        account_id: int,
        *,
        name: str,
        kind: str,
        institution: str,
        notes: str,
        balance: Decimal,
        opened_on: date | None = None,
        annual_fee_percent: Decimal = Decimal("0"),
        annual_fee_fixed: Decimal = Decimal("0"),
        availability_days: int = 0,
        details: dict[str, str] | None = None,
    ) -> None:
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
            account.details_encrypted = self._encrypt_details(details)
            account.kind = kind
            account.opened_on = opened_on
            account.annual_fee_percent = annual_fee_percent
            account.annual_fee_fixed = annual_fee_fixed
            account.availability_days = max(0, availability_days)
            account.current_balance = balance
            if balance != old_balance:
                delta = balance - old_balance
                session.add(
                    Transaction(
                        account_id=account.id,
                        booked_on=date.today(),
                        category="Ajustement de solde",
                        label_encrypted=self._crypto.encrypt("Ajustement manuel de solde"),
                        amount=delta,
                        is_shared=account.household_id is not None,
                    )
                )
                session.add(
                    AccountSnapshot(
                        account_id=account.id,
                        captured_on=date.today(),
                        balance=balance,
                        source="ajustement",
                        note_encrypted=self._crypto.encrypt("Modification manuelle du solde"),
                    )
                )

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

    def add_account_snapshot(
        self,
        user_id: int,
        account_id: int,
        captured_on: date,
        balance: Decimal,
        note: str = "",
    ) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
            session.add(
                AccountSnapshot(
                    account_id=account_id,
                    captured_on=captured_on,
                    balance=balance,
                    source="manuel",
                    note_encrypted=self._crypto.encrypt(note.strip()),
                )
            )
            if captured_on == date.today():
                account.current_balance = balance

    def account_history(self, user_id: int, account_id: int) -> list[dict[str, object]]:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or account not in self._visible_accounts(session, user_id):
                raise PermissionError("Compte non accessible.")
            snapshots = session.scalars(
                select(AccountSnapshot)
                .where(AccountSnapshot.account_id == account_id)
                .order_by(
                    AccountSnapshot.captured_on.asc(),
                    AccountSnapshot.id.asc(),
                )
            ).all()
            return [
                {
                    "date": item.captured_on,
                    "balance": Decimal(item.balance),
                    "source": item.source,
                    "note": self._crypto.decrypt(item.note_encrypted)
                    if item.note_encrypted
                    else "",
                }
                for item in snapshots
            ]

    def add_transaction(
        self,
        user_id: int,
        account_id: int,
        booked_on: date,
        category: str,
        label: str,
        amount: Decimal,
        *,
        is_shared: bool,
    ) -> int:
        if amount == 0:
            raise ValueError("Le montant d'une transaction ne peut pas être nul.")
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
            account.current_balance = Decimal(account.current_balance) + amount
            transaction = Transaction(
                account_id=account_id,
                booked_on=booked_on,
                category=category.strip() or "Autre",
                label_encrypted=self._crypto.encrypt(label.strip()),
                amount=amount,
                is_shared=is_shared,
            )
            session.add(transaction)
            session.flush()
            session.add(
                AccountSnapshot(
                    account_id=account_id,
                    captured_on=booked_on,
                    balance=account.current_balance,
                    source="transaction",
                    note_encrypted=self._crypto.encrypt(label.strip()),
                )
            )
            return transaction.id

    def list_transactions(
        self,
        user_id: int,
        account_id: int | None = None,
    ) -> list[dict[str, object]]:
        with self._database.session() as session:
            visible = self._visible_accounts(session, user_id)
            account_map = {account.id: account for account in visible}
            account_ids = list(account_map)
            if account_id is not None:
                if account_id not in account_map:
                    raise PermissionError("Compte non accessible.")
                account_ids = [account_id]
            if not account_ids:
                return []
            rows = session.scalars(
                select(Transaction)
                .where(Transaction.account_id.in_(account_ids))
                .order_by(Transaction.booked_on.desc(), Transaction.id.desc())
            ).all()
            return [
                {
                    "id": row.id,
                    "account_id": row.account_id,
                    "account": self._crypto.decrypt(
                        account_map[row.account_id].name_encrypted
                    ),
                    "date": row.booked_on,
                    "category": row.category,
                    "label": self._crypto.decrypt(row.label_encrypted),
                    "amount": Decimal(row.amount),
                    "shared": row.is_shared,
                }
                for row in rows
            ]

    def update_transaction(
        self,
        user_id: int,
        transaction_id: int,
        *,
        amount: Decimal,
        category: str,
        label: str,
    ) -> None:
        if amount == 0:
            raise ValueError("Le montant d'une transaction ne peut pas être nul.")
        with self._database.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                raise ValueError("Transaction introuvable.")
            account = session.get(FinancialAccount, transaction.account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur cette transaction.")
            account.current_balance = (
                Decimal(account.current_balance) - Decimal(transaction.amount) + amount
            )
            transaction.amount = amount
            transaction.category = category.strip() or "Autre"
            transaction.label_encrypted = self._crypto.encrypt(label.strip())
            session.add(
                AccountSnapshot(
                    account_id=account.id,
                    captured_on=date.today(),
                    balance=account.current_balance,
                    source="transaction",
                    note_encrypted=self._crypto.encrypt("Transaction modifiée"),
                )
            )

    def delete_transaction(self, user_id: int, transaction_id: int) -> None:
        with self._database.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                return
            account = session.get(FinancialAccount, transaction.account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur cette transaction.")
            account.current_balance = Decimal(account.current_balance) - Decimal(
                transaction.amount
            )
            session.delete(transaction)
            session.add(
                AccountSnapshot(
                    account_id=account.id,
                    captured_on=date.today(),
                    balance=account.current_balance,
                    source="transaction",
                    note_encrypted=self._crypto.encrypt("Transaction supprimée"),
                )
            )

    def add_asset(
        self,
        user_id: int,
        account_id: int,
        label: str,
        asset_kind: str,
        value: Decimal,
        sector: str,
        geography: str,
        expected_return: Decimal,
    ) -> None:
        with self._database.session() as session:
            account = session.get(FinancialAccount, account_id)
            if account is None or not self._can_manage_account(session, user_id, account):
                raise PermissionError("Vous n'avez pas les droits sur ce compte.")
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

    def record_snapshot(self, user_id: int) -> None:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return
        totals = self._calculate_totals(user_id)
        with self._database.session() as session:
            snapshot = session.scalar(
                select(NetWorthSnapshot).where(
                    NetWorthSnapshot.household_id == household_id,
                    NetWorthSnapshot.captured_on == date.today(),
                )
            )
            if snapshot:
                snapshot.gross_assets = totals["gross"]
                snapshot.liabilities = totals["liabilities"]
                snapshot.net_worth = totals["net"]
            else:
                session.add(
                    NetWorthSnapshot(
                        household_id=household_id,
                        captured_on=date.today(),
                        gross_assets=totals["gross"],
                        liabilities=totals["liabilities"],
                        net_worth=totals["net"],
                    )
                )

    def net_worth_history(self, user_id: int) -> list[dict[str, object]]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return []
        with self._database.session() as session:
            rows = session.scalars(
                select(NetWorthSnapshot)
                .where(NetWorthSnapshot.household_id == household_id)
                .order_by(NetWorthSnapshot.captured_on.asc())
            ).all()
            return [
                {
                    "date": row.captured_on,
                    "gross": Decimal(row.gross_assets),
                    "liabilities": Decimal(row.liabilities),
                    "net": Decimal(row.net_worth),
                }
                for row in rows
            ]

    def _calculate_totals(self, user_id: int) -> dict[str, Decimal]:
        accounts = self.list_accounts(user_id)
        gross = sum(
            (Decimal(row["balance"]) for row in accounts if not row["liability"]),
            Decimal("0"),
        )
        liabilities = sum(
            (
                abs(Decimal(row["balance"]))
                for row in accounts
                if row["liability"]
            ),
            Decimal("0"),
        )
        return {"gross": gross, "liabilities": liabilities, "net": gross - liabilities}

    def projection(
        self,
        user_id: int,
        model: str = "central",
        years: int = 10,
    ) -> list[object]:
        if years not in {1, 3, 5, 10, 15, 20, 25, 30}:
            raise ValueError("Horizon de projection non pris en charge.")
        totals = self._calculate_totals(user_id)
        dashboard = self.dashboard(user_id, include_projection=False)
        if model == "allocation":
            annual_return = Decimal(dashboard["expected_return"])
        else:
            annual_return = PROJECTION_MODELS.get(model, PROJECTION_MODELS["central"])
        return project_compound(
            max(totals["net"], Decimal("0")),
            annual_return,
            years=years,
        )

    def budget_summary(self, user_id: int) -> list[dict[str, object]]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return []
        month = date.today().replace(day=1)
        accounts = self.list_accounts(user_id)
        account_ids = [int(row["id"]) for row in accounts]
        with self._database.session() as session:
            budgets = session.scalars(
                select(MonthlyBudget).where(
                    MonthlyBudget.household_id == household_id,
                    MonthlyBudget.month == month,
                )
            ).all()
            transactions = []
            if account_ids:
                transactions = session.scalars(
                    select(Transaction).where(
                        Transaction.account_id.in_(account_ids),
                        Transaction.booked_on >= month,
                        Transaction.is_shared.is_(True),
                    )
                ).all()
        planned = {row.category: Decimal(row.planned_amount) for row in budgets}
        spent: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for transaction in transactions:
            amount = Decimal(transaction.amount)
            if amount < 0:
                spent[transaction.category] += abs(amount)
        categories = sorted(set(planned) | set(spent))
        return [
            {
                "category": category,
                "planned": planned.get(category, Decimal("0")),
                "actual": spent.get(category, Decimal("0")),
                "remaining": planned.get(category, Decimal("0"))
                - spent.get(category, Decimal("0")),
            }
            for category in categories
        ]

    def dashboard(
        self,
        user_id: int,
        *,
        include_projection: bool = True,
    ) -> dict[str, object]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        account_rows = self.list_accounts(user_id)
        totals = self._calculate_totals(user_id)
        account_ids = [int(row["id"]) for row in account_rows]

        with self._database.session() as session:
            assets = (
                session.scalars(
                    select(AssetPosition).where(AssetPosition.account_id.in_(account_ids))
                ).all()
                if account_ids
                else []
            )
            transactions = (
                session.scalars(
                    select(Transaction)
                    .where(Transaction.account_id.in_(account_ids))
                    .order_by(Transaction.booked_on.desc(), Transaction.id.desc())
                ).all()
                if account_ids
                else []
            )
            expenses: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
            month = date.today().replace(day=1)
            for transaction in transactions:
                if transaction.booked_on >= month and Decimal(transaction.amount) < 0:
                    expenses[transaction.category] += abs(Decimal(transaction.amount))

            by_type = allocation_by(
                (asset.asset_kind, Decimal(asset.value)) for asset in assets
            )
            by_sector = allocation_by(
                (asset.sector, Decimal(asset.value)) for asset in assets
            )
            by_geography = allocation_by(
                (asset.geography, Decimal(asset.value)) for asset in assets
            )
            expected = weighted_expected_return(
                AllocationItem(
                    asset.asset_kind,
                    Decimal(asset.value),
                    Decimal(asset.expected_annual_return),
                )
                for asset in assets
            )
            first_of_month = date.today().replace(day=1)
            budgets = (
                session.scalars(
                    select(MonthlyBudget).where(
                        MonthlyBudget.household_id == household_id,
                        MonthlyBudget.month == first_of_month,
                    )
                ).all()
                if can_view
                else []
            )

        planned = sum((Decimal(budget.planned_amount) for budget in budgets), Decimal("0"))
        household_budget = self.budget_summary(user_id) if can_view else []
        household_spent = sum(
            (Decimal(row["actual"]) for row in household_budget),
            Decimal("0"),
        )
        forecast = (
            project_compound(
                max(totals["net"], Decimal("0")),
                expected or PROJECTION_MODELS["central"],
                years=10,
            )
            if include_projection
            else []
        )
        return {
            **totals,
            "expenses": dict(
                sorted(expenses.items(), key=lambda item: item[1], reverse=True)
            ),
            "allocation_type": by_type,
            "allocation_sector": by_sector,
            "allocation_geography": by_geography,
            "hhi": concentration_hhi([Decimal(asset.value) for asset in assets]),
            "expected_return": expected,
            "forecast": forecast,
            "budget_planned": planned,
            "budget_spent": household_spent,
            "accounts": account_rows,
            "transaction_count": len(transactions),
            "recent_transactions": self.list_transactions(user_id)[:6],
        }

    def investment_analysis(self, user_id: int, profile: str) -> dict[str, object]:
        data = self.dashboard(user_id)
        target = INVESTMENT_PROFILES.get(profile, INVESTMENT_PROFILES["equilibre"])
        allocation = data["allocation_type"]
        total = sum((Decimal(value) for value in allocation.values()), Decimal("0"))
        current_pct: dict[str, Decimal] = {}
        if total > 0:
            for key, value in allocation.items():
                current_pct[str(key)] = Decimal(value) / total * Decimal("100")
        return {
            "profile": profile,
            "target": target,
            "current_pct": current_pct,
            "hhi": data["hhi"],
            "expected_return": data["expected_return"],
            "by_sector": data["allocation_sector"],
            "by_geography": data["allocation_geography"],
        }

    def set_budget(self, user_id: int, category: str, amount: Decimal) -> None:
        household_id, _, role, _ = self.household_for_user(user_id)
        if role != "admin_foyer":
            raise PermissionError("Seul l'admin_foyer peut modifier le budget du foyer.")
        category = category.strip() or "Autre"
        if amount < 0:
            raise ValueError("Le budget prévu doit être positif.")
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

    def create_household_project(
        self,
        user_id: int,
        name: str,
        kind: str,
        target_amount: Decimal,
        status: str,
        notes: str = "",
    ) -> int:
        household_id, _, role, _ = self.household_for_user(user_id)
        if role != "admin_foyer":
            raise PermissionError("Seul l'admin_foyer peut créer un budget de projet.")
        if not name.strip():
            raise ValueError("Le nom du projet est obligatoire.")
        with self._database.session() as session:
            project = HouseholdProject(
                household_id=household_id,
                name=name.strip(),
                kind=kind.strip() or "projet",
                target_amount=max(target_amount, Decimal("0")),
                status=status.strip() or "prévu",
                notes_encrypted=self._crypto.encrypt(notes.strip()),
            )
            session.add(project)
            session.flush()
            return project.id

    def add_project_contribution(
        self,
        user_id: int,
        project_id: int,
        member_user_id: int,
        contribution_kind: str,
        amount: Decimal,
        monthly_amount: Decimal,
        duration_months: int,
        account_id: int | None,
        status: str,
    ) -> int:
        household_id, _, role, _ = self.household_for_user(user_id)
        if role != "admin_foyer":
            raise PermissionError("Seul l'admin_foyer peut répartir un projet.")
        with self._database.session() as session:
            project = session.get(HouseholdProject, project_id)
            membership = session.scalar(
                select(HouseholdMember).where(
                    HouseholdMember.household_id == household_id,
                    HouseholdMember.user_id == member_user_id,
                )
            )
            if project is None or project.household_id != household_id:
                raise ValueError("Projet introuvable.")
            if membership is None:
                raise ValueError("Membre introuvable dans le foyer.")
            contribution = HouseholdProjectContribution(
                project_id=project_id,
                member_user_id=member_user_id,
                account_id=account_id,
                contribution_kind=contribution_kind.strip() or "autre",
                amount=max(amount, Decimal("0")),
                monthly_amount=max(monthly_amount, Decimal("0")),
                duration_months=max(0, duration_months),
                status=status.strip() or "prévu",
            )
            session.add(contribution)
            session.flush()
            return contribution.id

    def list_household_projects(self, user_id: int) -> list[dict[str, object]]:
        household_id, _, _, can_view = self.household_for_user(user_id)
        if not can_view:
            return []
        with self._database.session() as session:
            projects = session.scalars(
                select(HouseholdProject)
                .where(HouseholdProject.household_id == household_id)
                .order_by(HouseholdProject.created_at.desc())
            ).all()
            results: list[dict[str, object]] = []
            for project in projects:
                contributions = session.scalars(
                    select(HouseholdProjectContribution).where(
                        HouseholdProjectContribution.project_id == project.id
                    )
                ).all()
                shares = []
                for contribution in contributions:
                    member = session.get(User, contribution.member_user_id)
                    shares.append(
                        {
                            "id": contribution.id,
                            "member_user_id": contribution.member_user_id,
                            "member": member.display_name if member else "Membre",
                            "kind": contribution.contribution_kind,
                            "amount": Decimal(contribution.amount),
                            "monthly_amount": Decimal(contribution.monthly_amount),
                            "duration_months": contribution.duration_months,
                            "account_id": contribution.account_id,
                            "status": contribution.status,
                        }
                    )
                results.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "kind": project.kind,
                        "target_amount": Decimal(project.target_amount),
                        "status": project.status,
                        "notes": self._crypto.decrypt(project.notes_encrypted)
                        if project.notes_encrypted
                        else "",
                        "shares": shares,
                    }
                )
            return results
