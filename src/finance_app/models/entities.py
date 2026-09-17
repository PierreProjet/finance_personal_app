from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class HouseholdRole(StrEnum):
    ADMIN = "admin_foyer"
    MEMBER = "membre"


class AccountKind(StrEnum):
    CASH = "liquidites"
    CHECKING = "compte_courant"
    SAVINGS = "epargne"
    INVESTMENT = "investissement"
    LOAN = "credit"


class AssetKind(StrEnum):
    CASH = "liquidites"
    EQUITY = "actions"
    ETF = "etf"
    BOND = "obligations"
    REAL_ESTATE = "immobilier"
    CRYPTO = "crypto"
    PRIVATE_EQUITY = "non_cote"
    OTHER = "autre"


class ProjectStatus(StrEnum):
    PLANNED = "prévu"
    ACTIVE = "actif"
    PAUSED = "en_pause"
    COMPLETED = "terminé"


class ContributionKind(StrEnum):
    CASH = "cash"
    MONTHLY = "mensualité"
    LOAN = "prêt"
    TRANSFER = "virement"
    OTHER = "autre"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    accent_color: Mapped[str] = mapped_column(String(20), default="#6C63FF")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    memberships: Mapped[list[HouseholdMember]] = relationship(back_populates="user")


class Household(Base):
    __tablename__ = "households"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    members: Mapped[list[HouseholdMember]] = relationship(back_populates="household")


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (UniqueConstraint("household_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(30), default=HouseholdRole.MEMBER.value)
    can_view_household: Mapped[bool] = mapped_column(Boolean, default=True)
    household: Mapped[Household] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    household_id: Mapped[int | None] = mapped_column(
        ForeignKey("households.id"), nullable=True
    )
    name_encrypted: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(40))
    institution_encrypted: Mapped[str] = mapped_column(String(500), default="")
    notes_encrypted: Mapped[str] = mapped_column(String(2000), default="")
    details_encrypted: Mapped[str] = mapped_column(String(4000), default="")
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    annual_fee_percent: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0")
    )
    annual_fee_fixed: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )
    availability_days: Mapped[int] = mapped_column(Integer, default=0)
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )
    is_liability: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="CASCADE")
    )
    captured_on: Mapped[date] = mapped_column(Date, default=date.today)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source: Mapped[str] = mapped_column(String(30), default="system")
    note_encrypted: Mapped[str] = mapped_column(String(1000), default="")


class AssetPosition(Base):
    __tablename__ = "asset_positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="CASCADE")
    )
    label_encrypted: Mapped[str] = mapped_column(String(500))
    asset_kind: Mapped[str] = mapped_column(String(40))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    sector: Mapped[str] = mapped_column(String(100), default="Non renseigné")
    geography: Mapped[str] = mapped_column(String(100), default="Non renseigné")
    expected_annual_return: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), default=Decimal("0.04")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="CASCADE")
    )
    booked_on: Mapped[date] = mapped_column(Date, default=date.today)
    category: Mapped[str] = mapped_column(String(100), index=True)
    label_encrypted: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)


class MonthlyBudget(Base):
    __tablename__ = "monthly_budgets"
    __table_args__ = (UniqueConstraint("household_id", "month", "category"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    month: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(100))
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class HouseholdProject(Base):
    __tablename__ = "household_projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(140))
    kind: Mapped[str] = mapped_column(String(80), default="projet")
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(30), default=ProjectStatus.PLANNED.value)
    notes_encrypted: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HouseholdProjectContribution(Base):
    __tablename__ = "household_project_contributions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("household_projects.id", ondelete="CASCADE")
    )
    member_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="SET NULL"), nullable=True
    )
    contribution_kind: Mapped[str] = mapped_column(
        String(40), default=ContributionKind.CASH.value
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    monthly_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0")
    )
    duration_months: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="prévu")


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    captured_on: Mapped[date] = mapped_column(Date, default=date.today)
    gross_assets: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 2))
