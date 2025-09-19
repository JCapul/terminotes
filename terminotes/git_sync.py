"""Integration with Git for syncing the notes repository."""

from __future__ import annotations


class GitSync:
    """Placeholder wrapper around Git commands for committing and pushing notes."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    def record_note(self, note_id: str) -> None:
        """Stage, commit, and push a note represented by ``note_id``."""
        raise NotImplementedError("Git synchronization pending implementation.")
