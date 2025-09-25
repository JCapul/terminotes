"""SQLite-backed persistence layer for Terminotes."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

DB_FILENAME = "terminotes.sqlite3"
SELECT_COLUMNS = "id, title, body, description, created_at, updated_at, can_publish"
TABLE_NOTES = "notes"


@dataclass(slots=True)
class Note:
    """Representation of a stored note."""

    id: int
    title: str
    body: str
    description: str
    created_at: datetime
    updated_at: datetime
    can_publish: bool


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
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    can_publish INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._ensure_columns(conn)

    # ------------------------------------------------------------------
    # Note operations
    # ------------------------------------------------------------------
    def create_note(
        self,
        title: str,
        body: str,
        description: str = "",
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        can_publish: bool = False,
    ) -> Note:
        """Persist a new note and return the resulting ``Note`` instance."""

        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot create an empty note.")

        created = created_at or datetime.now(tz=timezone.utc)
        updated = updated_at or created

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    (
                        "INSERT INTO notes (title, body, description, "
                        "created_at, updated_at, can_publish) "
                        "VALUES (?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        title,
                        body,
                        description,
                        created.isoformat(),
                        updated.isoformat(),
                        1 if can_publish else 0,
                    ),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return Note(
            id=int(cursor.lastrowid),
            title=title,
            body=body,
            description=description,
            created_at=created,
            updated_at=updated,
            can_publish=can_publish,
        )

    def list_notes(self, limit: int = 10) -> Iterable[Note]:
        """Return up to ``limit`` most recently updated notes.

        Notes are ordered by ``updated_at`` descending (most recent first).
        """
        if limit <= 0:
            return []

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    (
                        f"SELECT {SELECT_COLUMNS} FROM {TABLE_NOTES} "
                        "ORDER BY updated_at DESC LIMIT ?"
                    ),
                    (int(limit),),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to list notes: {exc}") from exc

            rows = cursor.fetchall()

        return [self._row_to_note(r) for r in rows]

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
        self,
        note_id: int,
        title: str,
        body: str,
        description: str = "",
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        can_publish: bool | None = None,
    ) -> Note:
        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot update note with empty content.")

        # Determine new timestamps
        new_updated = updated_at or datetime.now(tz=timezone.utc)

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE notes
                SET title = ?, body = ?, description = ?, updated_at = ?,
                    can_publish = COALESCE(?, can_publish)
                WHERE id = ?
                """,
                (
                    title,
                    body,
                    description,
                    new_updated.isoformat(),
                    (None if can_publish is None else (1 if can_publish else 0)),
                    int(note_id),
                ),
            )
            if cursor.rowcount == 0:
                raise StorageError(f"Note '{note_id}' not found.")

            # Update created_at if explicitly provided
            if created_at is not None:
                conn.execute(
                    "UPDATE notes SET created_at = ? WHERE id = ?",
                    (created_at.isoformat(), int(note_id)),
                )

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
                f"SELECT {SELECT_COLUMNS} FROM {TABLE_NOTES} "
                "ORDER BY updated_at DESC LIMIT 1"
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

    def delete_note(self, note_id: int) -> None:
        """Delete a note by its id.

        Raises ``StorageError`` if the note does not exist.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notes WHERE id = ?",
                (int(note_id),),
            )
            if cursor.rowcount == 0:
                raise StorageError(f"Note '{note_id}' not found.")

    def search_notes(self, pattern: str) -> Iterable[Note]:
        # Very simple case-insensitive substring match across title, body, description.
        # Caller is responsible for validating non-empty pattern and limit control.
        text = str(pattern)
        if not text:
            return []

        # Escape LIKE wildcards and backslash, then surround with %...%
        def _escape_like(s: str) -> str:
            s = s.replace("\\", "\\\\")
            s = s.replace("%", "\\%")
            s = s.replace("_", "\\_")
            return s

        like = f"%{_escape_like(text)}%"

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    (
                        f"SELECT {SELECT_COLUMNS} FROM {TABLE_NOTES} "
                        "WHERE LOWER(title) LIKE LOWER(?) ESCAPE '\\' "
                        "   OR LOWER(body) LIKE LOWER(?) ESCAPE '\\' "
                        "   OR LOWER(description) LIKE LOWER(?) ESCAPE '\\' "
                        "ORDER BY updated_at DESC"
                    ),
                    (like, like, like),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to search notes: {exc}") from exc

            rows = cursor.fetchall()

        return [self._row_to_note(r) for r in rows]

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
        """Reserved for future schema migrations (no-op for now)."""
        return

    def _row_to_note(self, row: sqlite3.Row | Sequence[str]) -> Note:
        (
            note_id,
            title,
            body,
            description,
            created_at_raw,
            updated_at_raw,
            can_publish_raw,
        ) = row

        return Note(
            id=int(note_id),
            title=title,
            body=body,
            description=description,
            created_at=datetime.fromisoformat(created_at_raw),
            updated_at=datetime.fromisoformat(updated_at_raw),
            can_publish=bool(int(can_publish_raw)),
        )
