"""SQLite-backed persistence layer for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(slots=True)
class Note:
    """Representation of a stored note."""

    note_id: str
    content: str
    tags: tuple[str, ...]


class Storage:
    """Placeholder abstraction over the SQLite database."""

    def __init__(self, path: str) -> None:
        self.path = path

    def initialize(self) -> None:
        raise NotImplementedError("Database initialization pending implementation.")

    def create_note(self, content: str, tags: Sequence[str]) -> Note:
        raise NotImplementedError("Note creation pending implementation.")

    def list_notes(self, limit: int = 10) -> Iterable[Note]:
        raise NotImplementedError("Listing notes pending implementation.")

    def fetch_note(self, note_id: str) -> Note:
        raise NotImplementedError("Fetching notes pending implementation.")

    def update_note(self, note_id: str, content: str, tags: Sequence[str]) -> Note:
        raise NotImplementedError("Updating notes pending implementation.")

    def search_notes(self, pattern: str) -> Iterable[Note]:
        raise NotImplementedError("Search pending implementation.")
