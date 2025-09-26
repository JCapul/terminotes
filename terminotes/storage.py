"""Peewee-backed persistence layer for Terminotes."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from peewee import (
    AutoField,
    BooleanField,
    DoesNotExist,
    Model,
    SqliteDatabase,
    TextField,
    fn,
)

DB_FILENAME = "terminotes.sqlite3"
TABLE_NOTES = "notes"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _coerce_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return _utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StorageError(RuntimeError):
    """Raised when interacting with the notes database fails."""


class UTCTextDateField(TextField):
    """Store ISO-8601 timestamps while returning timezone-aware datetimes."""

    def python_value(self, value: str | None) -> datetime | None:  # type: ignore[override]
        if value is None:
            return None
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    def db_value(self, value: datetime | None) -> str | None:  # type: ignore[override]
        if value is None:
            return None
        coerced = _coerce_utc(value)
        return coerced.isoformat()


class StorageDatabase(SqliteDatabase):
    """SqliteDatabase configured for per-call connection lifetimes."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            str(path),
            pragmas={"foreign_keys": 1},
            check_same_thread=False,
        )


class StorageModel(Model):
    """Base model bound to the storage database."""

    class Meta:
        database = SqliteDatabase(None)


class Note(StorageModel):
    """Peewee model representing a stored note."""

    id = AutoField()
    title = TextField(null=False)
    body = TextField(null=False)
    description = TextField(default="", null=False)
    created_at = UTCTextDateField(default=_utc_now, null=False)
    updated_at = UTCTextDateField(default=_utc_now, null=False)
    can_publish = BooleanField(default=False, null=False)

    class Meta:
        table_name = TABLE_NOTES


class Storage:
    """High-level helper for interacting with the Terminotes database."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._database = StorageDatabase(self.path)

    def initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem failures are rare
            raise StorageError(f"Failed to create database directory: {exc}") from exc

        with self._binding() as note_model:
            try:
                note_model.create_table(safe=True)
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to initialize database: {exc}") from exc

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
        normalized_title = title.strip()
        normalized_body = body.rstrip()
        if not (normalized_title or normalized_body):
            raise StorageError("Cannot create an empty note.")

        created = _coerce_utc(created_at)
        updated = _coerce_utc(updated_at) if updated_at is not None else created

        with self._binding() as note_model:
            try:
                note = note_model.create(
                    title=normalized_title,
                    body=normalized_body,
                    description=description,
                    created_at=created,
                    updated_at=updated,
                    can_publish=can_publish,
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return note

    def list_notes(self, limit: int = 10) -> list[Note]:
        if limit <= 0:
            return []

        with self._binding() as note_model:
            query = (
                note_model.select()
                .order_by(note_model.updated_at.desc())
                .limit(int(limit))
            )
            return list(query)

    def fetch_note(self, note_id: int) -> Note:
        with self._binding() as note_model:
            try:
                return note_model.get_by_id(int(note_id))
            except DoesNotExist:
                raise StorageError(f"Note '{note_id}' not found.") from None

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
        normalized_title = title.strip()
        normalized_body = body.rstrip()
        if not (normalized_title or normalized_body):
            raise StorageError("Cannot update note with empty content.")

        new_updated = _coerce_utc(updated_at)
        new_created = _coerce_utc(created_at) if created_at is not None else None

        with self._binding() as note_model:
            try:
                note = note_model.get_by_id(int(note_id))
            except DoesNotExist:
                raise StorageError(f"Note '{note_id}' not found.") from None

            note.title = normalized_title
            note.body = normalized_body
            note.description = description
            note.updated_at = new_updated
            if new_created is not None:
                note.created_at = new_created
            if can_publish is not None:
                note.can_publish = can_publish

            note.save()
            return note

    def fetch_last_updated_note(self) -> Note:
        with self._binding() as note_model:
            note = (
                note_model.select()
                .order_by(note_model.updated_at.desc())
                .limit(1)
                .first()
            )
            if note is None:
                raise StorageError("No notes available.")
            return note

    def count_notes(self) -> int:
        with self._binding() as note_model:
            return note_model.select().count()

    def delete_note(self, note_id: int) -> None:
        with self._binding() as note_model:
            deleted = note_model.delete().where(note_model.id == int(note_id)).execute()
            if deleted == 0:
                raise StorageError(f"Note '{note_id}' not found.")

    def search_notes(self, pattern: str) -> list[Note]:
        text = str(pattern)
        if not text:
            return []

        with self._binding() as note_model:
            lowered = text.lower()
            query = (
                note_model.select()
                .where(
                    (fn.LOWER(note_model.title).contains(lowered))
                    | (fn.LOWER(note_model.body).contains(lowered))
                    | (fn.LOWER(note_model.description).contains(lowered))
                )
                .order_by(note_model.updated_at.desc())
            )
            return list(query)

    @contextmanager
    def _binding(self) -> Iterator[type[Note]]:
        with self._database.connection_context():
            with Note.bind_ctx(self._database):
                yield Note
