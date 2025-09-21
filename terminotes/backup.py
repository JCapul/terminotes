"""Backup abstraction for Terminotes storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .git_sync import GitSync, GitSyncError


class BackupError(RuntimeError):
    """Raised when executing a backup operation fails."""


class BackupProvider(ABC):
    """Common interface for backup providers."""

    @abstractmethod
    def prepare(self) -> None:
        """Perform any setup required before backups can run."""

    @abstractmethod
    def backup(self, database_path: Path) -> None:
        """Execute a backup for the given database path."""


class NoopBackup(BackupProvider):
    """Backup provider that performs no work."""

    def prepare(self) -> None:  # pragma: no cover - trivial
        return

    def backup(self, database_path: Path) -> None:  # pragma: no cover - trivial
        return


class GitBackup(BackupProvider):
    """Backup provider that relies on a git repository as storage."""

    def __init__(self, git_sync: GitSync) -> None:
        self.git_sync = git_sync

    def prepare(self) -> None:
        try:
            self.git_sync.ensure_local_clone()
        except GitSyncError as exc:
            raise BackupError(str(exc)) from exc

    def backup(self, database_path: Path) -> None:
        # Stage 4 will implement commit/push behaviour. For now we simply ensure
        # the clone remains available so future backups can commit state.
        try:
            self.git_sync.ensure_local_clone()
        except GitSyncError as exc:
            raise BackupError(str(exc)) from exc
