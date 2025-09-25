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
SELECT_COLUMNS = (
    "id, title, body, description, tags, created_at, updated_at, can_publish, type"
)
TABLE_NOTES = "notes"


@dataclass(slots=True)
class Note:
    """Representation of a stored note."""

    id: int
    title: str
    body: str
    description: str
    tags: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    can_publish: bool
    type: str


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
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    can_publish INTEGER NOT NULL DEFAULT 0,
                    type TEXT NOT NULL DEFAULT 'note'
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
        tags: Sequence[str],
        description: str = "",
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        can_publish: bool = False,
        note_type: str = "note",
    ) -> Note:
        """Persist a new note and return the resulting ``Note`` instance."""

        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot create an empty note.")

        normalized_tags = tuple(tags)
        created = created_at or datetime.now(tz=timezone.utc)
        updated = updated_at or created
        encoded_tags = json.dumps(list(normalized_tags))

        with self._connection() as conn:
            try:
                cursor = conn.execute(
                    (
                        "INSERT INTO notes (title, body, description, tags, "
                        "created_at, updated_at, can_publish, type) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        title,
                        body,
                        description,
                        encoded_tags,
                        created.isoformat(),
                        updated.isoformat(),
                        1 if can_publish else 0,
                        note_type,
                    ),
                )
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return Note(
            id=int(cursor.lastrowid),
            title=title,
            body=body,
            description=description,
            tags=normalized_tags,
            created_at=created,
            updated_at=updated,
            can_publish=can_publish,
            type=note_type,
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
        self,
        note_id: int,
        title: str,
        body: str,
        tags: Sequence[str],
        description: str = "",
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        can_publish: bool | None = None,
        note_type: str | None = None,
    ) -> Note:
        title = title.strip()
        body = body.rstrip()
        if not (title or body):
            raise StorageError("Cannot update note with empty content.")

        # Determine new timestamps
        new_updated = updated_at or datetime.now(tz=timezone.utc)
        encoded_tags = json.dumps(list(tags))

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE notes
                SET title = ?, body = ?, description = ?, tags = ?, updated_at = ?,
                    can_publish = COALESCE(?, can_publish),
                    type = COALESCE(?, type)
                WHERE id = ?
                """,
                (
                    title,
                    body,
                    description,
                    encoded_tags,
                    new_updated.isoformat(),
                    (None if can_publish is None else (1 if can_publish else 0)),
                    note_type,
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
        """Ensure expected columns exist and migrate legacy fields.

        - Adds missing 'can_publish' column (renamed from legacy 'published').
        - Copies legacy values from 'published' into 'can_publish' when upgrading.
        - Ensures 'type' column exists.
        """
        try:
            cur = conn.execute("PRAGMA table_info(notes)")
            cols = {str(r[1]) for r in cur.fetchall()}

            added_can_publish = False
            if "can_publish" not in cols:
                conn.execute(
                    (
                        "ALTER TABLE notes ADD COLUMN can_publish "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
                added_can_publish = True

            if "type" not in cols:
                conn.execute(
                    "ALTER TABLE notes ADD COLUMN type TEXT NOT NULL DEFAULT 'note'"
                )

            # If upgrading from legacy schema where 'published' existed, migrate values.
            if added_can_publish and "published" in cols:
                try:
                    conn.execute("UPDATE notes SET can_publish = published")
                except sqlite3.DatabaseError:
                    # Best-effort migration; ignore if legacy column missing.
                    pass
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise StorageError(f"Failed to ensure schema columns: {exc}") from exc

    def _row_to_note(self, row: sqlite3.Row | Sequence[str]) -> Note:
        (
            note_id,
            title,
            body,
            description,
            tags_raw,
            created_at_raw,
            updated_at_raw,
            can_publish_raw,
            type_raw,
        ) = row
        try:
            tags = tuple(json.loads(tags_raw))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise StorageError("Stored tags payload is corrupted.") from exc

        return Note(
            id=int(note_id),
            title=title,
            body=body,
            description=description,
            tags=tags,
            created_at=datetime.fromisoformat(created_at_raw),
            updated_at=datetime.fromisoformat(updated_at_raw),
            can_publish=bool(int(can_publish_raw)),
            type=str(type_raw),
        )
