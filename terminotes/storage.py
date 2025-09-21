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


@dataclass(slots=True)
class Note:
    """Representation of a stored note."""

    note_id: str
    content: str
    tags: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


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
                    note_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
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
    def create_note(self, content: str, tags: Sequence[str]) -> Note:
        """Persist a new note and return the resulting ``Note`` instance."""

        content = content.rstrip()
        if not content:
            raise StorageError("Cannot create an empty note.")

        normalized_tags = tuple(tags)
        created_at = datetime.now(tz=timezone.utc)
        updated_at = created_at
        note_id = self._generate_note_id(created_at)
        encoded_tags = json.dumps(list(normalized_tags))

        with self._connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO notes (note_id, content, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        note_id,
                        content,
                        encoded_tags,
                        created_at.isoformat(),
                        updated_at.isoformat(),
                    ),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return Note(
            note_id=note_id,
            content=content,
            tags=normalized_tags,
            created_at=created_at,
            updated_at=updated_at,
        )

    def list_notes(self, limit: int = 10) -> Iterable[Note]:
        raise NotImplementedError("Listing notes pending implementation.")

    def fetch_note(self, note_id: str) -> Note:
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT note_id, content, tags, created_at, updated_at FROM notes WHERE note_id = ?",
                (note_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise StorageError(f"Note '{note_id}' not found.")
        return self._row_to_note(row)

    def update_note(self, note_id: str, content: str, tags: Sequence[str]) -> Note:
        content = content.rstrip()
        if not content:
            raise StorageError("Cannot update note with empty content.")

        updated_at = datetime.now(tz=timezone.utc)
        encoded_tags = json.dumps(list(tags))

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE notes
                SET content = ?, tags = ?, updated_at = ?
                WHERE note_id = ?
                """,
                (content, encoded_tags, updated_at.isoformat(), note_id),
            )
            if cursor.rowcount == 0:
                raise StorageError(f"Note '{note_id}' not found.")

            cursor = conn.execute(
                "SELECT note_id, content, tags, created_at, updated_at FROM notes WHERE note_id = ?",
                (note_id,),
            )
            row = cursor.fetchone()

        if row is None:  # pragma: no cover - defensive
            raise StorageError(f"Note '{note_id}' not found after update.")

        return self._row_to_note(row)

    def fetch_last_updated_note(self) -> Note:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT note_id, content, tags, created_at, updated_at
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
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _generate_note_id(self, created_at: datetime) -> str:
        """Generate a deterministic note identifier.

        ``created_at`` is used to ensure chronological ordering is retained.
        """

        return created_at.strftime("%Y%m%d%H%M%S%f")

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(notes)")
        }
        if "updated_at" not in columns:
            conn.execute("ALTER TABLE notes ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
            conn.execute("UPDATE notes SET updated_at = created_at WHERE updated_at = ''")

    def _row_to_note(self, row: sqlite3.Row | Sequence[str]) -> Note:
        note_id, content, tags_raw, created_at_raw, updated_at_raw = row
        try:
            tags = tuple(json.loads(tags_raw))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise StorageError("Stored tags payload is corrupted.") from exc

        return Note(
            note_id=note_id,
            content=content,
            tags=tags,
            created_at=datetime.fromisoformat(created_at_raw),
            updated_at=datetime.fromisoformat(updated_at_raw),
        )
