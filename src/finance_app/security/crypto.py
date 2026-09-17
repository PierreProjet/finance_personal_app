from __future__ import annotations

import base64
import os
from contextlib import suppress
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

try:
    import keyring
except ImportError:  # pragma: no cover - dependency is declared, fallback is defensive.
    keyring = None  # type: ignore[assignment]


SERVICE_NAME = "FinanceFoyer"
KEY_ACCOUNT = "local-master-key"


class CryptoService:
    """Encrypt/decrypt sensitive application values using a local master key.

    The preferred storage is the operating-system credential store through `keyring`.
    A restricted local key file is used as a fallback for environments without keyring.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if keyring is not None:
            try:
                stored = keyring.get_password(SERVICE_NAME, KEY_ACCOUNT)
                if stored:
                    return stored.encode("ascii")
                generated = Fernet.generate_key()
                keyring.set_password(
                    SERVICE_NAME,
                    KEY_ACCOUNT,
                    generated.decode("ascii"),
                )
                return generated
            except Exception:
                pass

        key_path = self._data_dir / ".master.key"
        if key_path.exists():
            return key_path.read_bytes().strip()
        generated = Fernet.generate_key()
        key_path.write_bytes(generated)
        with suppress(OSError):
            os.chmod(key_path, 0o600)
        return generated

    def encrypt(self, value: str) -> str:
        token = self._fernet.encrypt(value.encode("utf-8"))
        return base64.urlsafe_b64encode(token).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            token = base64.urlsafe_b64decode(value.encode("ascii"))
            return self._fernet.decrypt(token).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Impossible de déchiffrer la donnée.") from exc
