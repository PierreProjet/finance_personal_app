from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class SyncStatus(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    SYNCING = "syncing"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class SyncResult:
    """Result returned by a future cloud synchronization provider."""

    status: SyncStatus
    uploaded_records: int = 0
    downloaded_records: int = 0
    conflicts: int = 0


class CloudSyncProvider(Protocol):
    """Future boundary for an opt-in cloud synchronization backend."""

    provider_name: str

    def synchronize(self, encrypted_backup: bytes) -> SyncResult:
        """Synchronize already encrypted application data."""
        ...


class DisabledCloudSyncProvider:
    """Explicit default: no cloud synchronization is performed."""

    provider_name = "disabled"

    def synchronize(self, encrypted_backup: bytes) -> SyncResult:
        """Refuse network synchronization until the feature is explicitly enabled."""
        raise RuntimeError("La synchronisation cloud n'est pas activée dans cette version.")
