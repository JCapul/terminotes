"""SQLite-backed persistence layer for Terminotes."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

DB_FILENAME = "terminotes.sqlite3"
SELECT_COLUMNS = "id, title, body, tags, created_at, updated_at"
TABLE_NOTES = "notes"


@dataclass(slots=True)
class Note:
    """Representation of a stored note."""

    id: int
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: datetime
    updated_at: datetime

    @property
    def content(self) -> str:
        if self.title:
            if self.body:
                return f"{self.title}\n\n{self.body}".strip()
            return self.title.strip()
        return self.body.strip()


class StorageError(RuntimeError):
    """Raised when interacting with the SQLite database fails."""


class Storage:
    """Abstraction over the Terminotes SQLite database."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Ensure the notes database exists with the expected schema."""

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem errors are rare
            raise StorageError(f"Failed to create database directory: {exc}") from exc

        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_columns(conn)

    # ------------------------------------------------------------------
    # Note operations
    # ------------------------------------------------------------------
    def create_note(self, title: str, body: str, tags: Sequence[str]) -> Note:
        """Persist a new note and return the resulting ``Note`` instance."""

        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot create an empty note.")

        normalized_tags = tuple(tags)
        created_at = datetime.now(tz=timezone.utc)
        updated_at = created_at
        encoded_tags = json.dumps(list(normalized_tags))

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO notes (title, body, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        body,
                        encoded_tags,
                        created_at.isoformat(),
                        updated_at.isoformat(),
                    ),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return Note(
            id=int(cursor.lastrowid),
            title=title,
            body=body,
            tags=normalized_tags,
            created_at=created_at,
            updated_at=updated_at,
        )

    def list_notes(self, limit: int = 10) -> Iterable[Note]:
        raise NotImplementedError("Listing notes pending implementation.")

    def fetch_note(self, note_id: int) -> Note:
        with self._connection() as conn:
            cursor = conn.execute(
                (f"SELECT {SELECT_COLUMNS} FROM {TABLE_NOTES} WHERE id = ?"),
                (int(note_id),),
            )
            row = cursor.fetchone()
        if row is None:
            raise StorageError(f"Note '{note_id}' not found.")
        return self._row_to_note(row)

    def update_note(
        self, note_id: int, title: str, body: str, tags: Sequence[str]
    ) -> Note:
        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot update note with empty content.")

        updated_at = datetime.now(tz=timezone.utc)
        encoded_tags = json.dumps(list(tags))

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE notes
                SET title = ?, body = ?, tags = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    body,
                    encoded_tags,
                    updated_at.isoformat(),
                    int(note_id),
                ),
            )
            if cursor.rowcount == 0:
                raise StorageError(f"Note '{note_id}' not found.")

            cursor = conn.execute(
                (f"SELECT {SELECT_COLUMNS} FROM {TABLE_NOTES} WHERE id = ?"),
                (int(note_id),),
            )
            row = cursor.fetchone()

        if row is None:  # pragma: no cover - defensive
            raise StorageError(f"Note '{note_id}' not found after update.")

        return self._row_to_note(row)

    def fetch_last_updated_note(self) -> Note:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, title, body, tags, created_at, updated_at
                FROM notes
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

        if row is None:
            raise StorageError("No notes available.")

        return self._row_to_note(row)

    def count_notes(self) -> int:
        with self._connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM notes")
            (count,) = cursor.fetchone()
        return int(count)

    def search_notes(self, pattern: str) -> Iterable[Note]:
        raise NotImplementedError("Search pending implementation.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # Integer primary keys are assigned by SQLite; no manual generation.

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        # No migrations performed; greenfield schema expected.
        pass

    def _row_to_note(self, row: sqlite3.Row | Sequence[str]) -> Note:
        note_id, title, body, tags_raw, created_at_raw, updated_at_raw = row
        try:
            tags = tuple(json.loads(tags_raw))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise StorageError("Stored tags payload is corrupted.") from exc

        return Note(
            id=int(note_id),
            title=title,
            body=body,
            tags=tags,
            created_at=datetime.fromisoformat(created_at_raw),
            updated_at=datetime.fromisoformat(updated_at_raw),
        )
