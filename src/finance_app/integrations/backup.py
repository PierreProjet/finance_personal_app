from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet


class EncryptedBackupService:
    """Encrypt and decrypt a local backup using an application Fernet key."""

    def __init__(self, key: bytes) -> None:
        self._cipher = Fernet(key)

    def export_bytes(self, database_bytes: bytes) -> bytes:
        """Return encrypted database bytes suitable for a manual backup."""
        return self._cipher.encrypt(database_bytes)

    def import_bytes(self, encrypted_bytes: bytes) -> bytes:
        """Decrypt a backup and raise if its integrity check fails."""
        return self._cipher.decrypt(encrypted_bytes)

    def export_file(self, source: Path, destination: Path) -> None:
        """Encrypt a local file into a destination backup."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.export_bytes(source.read_bytes()))

    def import_file(self, source: Path, destination: Path) -> None:
        """Restore an encrypted backup into a local file."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.import_bytes(source.read_bytes()))
