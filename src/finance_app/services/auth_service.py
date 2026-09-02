from __future__ import annotations

from sqlalchemy import select

from finance_app.db import Database
from finance_app.models.entities import Household, HouseholdMember, HouseholdRole, User
from finance_app.security.passwords import hash_password, verify_password


class AuthService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def register_user(
        self,
        username: str,
        password: str,
        display_name: str,
        accent_color: str,
        household_name: str,
    ) -> User:
        username = username.strip().lower()
        if not username:
            raise ValueError("Le nom d'utilisateur est obligatoire.")
        if not display_name.strip():
            raise ValueError("Le nom affiché est obligatoire.")
        if not household_name.strip():
            raise ValueError("Le nom du foyer est obligatoire.")

        with self._database.session() as session:
            if session.scalar(select(User).where(User.username == username)):
                raise ValueError("Ce nom d'utilisateur existe déjà.")
            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name.strip(),
                accent_color=accent_color,
            )
            household = Household(name=household_name.strip())
            session.add_all([user, household])
            session.flush()
            session.add(
                HouseholdMember(
                    household_id=household.id,
                    user_id=user.id,
                    role=HouseholdRole.ADMIN.value,
                    can_view_household=True,
                )
            )
            session.flush()
            return user

    def create_household_member(
        self,
        admin_user_id: int,
        username: str,
        password: str,
        display_name: str,
        accent_color: str = "#3A86FF",
        can_view_household: bool = True,
    ) -> User:
        """Create a user directly inside the admin's household."""
        username = username.strip().lower()
        with self._database.session() as session:
            admin_membership = session.scalar(
                select(HouseholdMember).where(HouseholdMember.user_id == admin_user_id)
            )
            if admin_membership is None or admin_membership.role != HouseholdRole.ADMIN.value:
                raise PermissionError("Seul l'admin_foyer peut créer un membre.")
            if session.scalar(select(User).where(User.username == username)):
                raise ValueError("Ce nom d'utilisateur existe déjà.")
            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name.strip(),
                accent_color=accent_color,
            )
            session.add(user)
            session.flush()
            session.add(
                HouseholdMember(
                    household_id=admin_membership.household_id,
                    user_id=user.id,
                    role=HouseholdRole.MEMBER.value,
                    can_view_household=can_view_household,
                )
            )
            session.flush()
            return user

    def set_household_visibility(
        self, admin_user_id: int, member_user_id: int, can_view_household: bool
    ) -> None:
        with self._database.session() as session:
            admin_membership = session.scalar(
                select(HouseholdMember).where(HouseholdMember.user_id == admin_user_id)
            )
            member = session.scalar(
                select(HouseholdMember).where(HouseholdMember.user_id == member_user_id)
            )
            if admin_membership is None or admin_membership.role != HouseholdRole.ADMIN.value:
                raise PermissionError("Seul l'admin_foyer peut modifier les permissions.")
            if member is None or member.household_id != admin_membership.household_id:
                raise ValueError("Membre introuvable dans ce foyer.")
            member.can_view_household = can_view_household

    def list_household_members(self, user_id: int) -> list[dict[str, object]]:
        with self._database.session() as session:
            membership = session.scalar(
                select(HouseholdMember).where(HouseholdMember.user_id == user_id)
            )
            if membership is None:
                return []
            members = session.scalars(
                select(HouseholdMember).where(
                    HouseholdMember.household_id == membership.household_id
                )
            ).all()
            return [
                {
                    "user_id": member.user_id,
                    "display_name": member.user.display_name,
                    "username": member.user.username,
                    "role": member.role,
                    "can_view_household": member.can_view_household,
                }
                for member in members
            ]

    def authenticate(self, username: str, password: str) -> User | None:
        with self._database.session() as session:
            user = session.scalar(select(User).where(User.username == username.strip().lower()))
            if user and verify_password(user.password_hash, password):
                return user
        return None
