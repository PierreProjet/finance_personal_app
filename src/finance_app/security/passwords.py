from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id using library-maintained secure defaults."""
    if len(password) < 10:
        raise ValueError("Le mot de passe doit contenir au moins 10 caractères.")
    return _hasher.hash(password)


def verify_password(password_hash: str, candidate: str) -> bool:
    """Return True only when *candidate* matches the stored Argon2 hash."""
    try:
        return _hasher.verify(password_hash, candidate)
    except (VerifyMismatchError, InvalidHashError):
        return False
