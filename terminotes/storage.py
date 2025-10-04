"""Peewee-backed persistence layer for Terminotes."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from peewee import (
    AutoField,
    BooleanField,
    DoesNotExist,
    ManyToManyField,
    Model,
    SqliteDatabase,
    TextField,
    fn,
    prefetch,
)

DB_FILENAME = "terminotes.sqlite3"
TABLE_NOTES = "notes"
TABLE_TAGS = "tags"

_UNSET = object()
ExtraData = dict[str, Any] | None


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _coerce_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return _utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_tag_name(raw: str) -> str | None:
    name = str(raw).strip().lower()
    return name or None


def _prepare_tags(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in tags:
        value = _normalize_tag_name(item)
        if value is None or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized


class StorageError(RuntimeError):
    """Raised when interacting with the notes database fails."""


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


class Tag(StorageModel):
    """Represents a unique tag label."""

    id = AutoField()
    name = TextField(unique=True)

    class Meta:
        table_name = TABLE_TAGS


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


class Note(StorageModel):
    """Peewee model representing a stored note."""

    id = AutoField()
    title = TextField(null=False)
    body = TextField(null=False)
    description = TextField(default="", null=False)
    created_at = UTCTextDateField(default=_utc_now, null=False)
    updated_at = UTCTextDateField(default=_utc_now, null=False)
    can_publish = BooleanField(default=False, null=False)
    extra_data = TextField(null=True)
    tags = ManyToManyField(Tag, backref="notes")

    class Meta:
        table_name = TABLE_NOTES


class Storage:
    """High-level helper for interacting with the Terminotes database."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._database = StorageDatabase(self.path)
        self._through_model = Note.tags.get_through_model()
        self._database.bind([Note, Tag, self._through_model])

    def initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem failures are rare
            raise StorageError(f"Failed to create database directory: {exc}") from exc

        with self._connection():
            try:
                self._database.create_tables(
                    [Tag, Note, self._through_model], safe=True
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to initialize database: {exc}") from exc

            self._ensure_extra_data_column()

    def create_note(
        self,
        title: str,
        body: str,
        description: str = "",
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        can_publish: bool = False,
        tags: Iterable[str] | None = None,
        extra_data: ExtraData = None,
    ) -> Note:
        normalized_title = title.strip()
        normalized_body = body.rstrip()
        if not (normalized_title or normalized_body):
            raise StorageError("Cannot create an empty note.")

        created = _coerce_utc(created_at)
        updated = _coerce_utc(updated_at) if updated_at is not None else created
        tag_names = _prepare_tags(tags)

        with self._connection():
            try:
                with self._database.atomic():
                    note = Note.create(
                        title=normalized_title,
                        body=normalized_body,
                        description=description,
                        created_at=created,
                        updated_at=updated,
                        can_publish=can_publish,
                        extra_data=self._dump_extra_data(extra_data),
                    )

                    if tag_names:
                        tag_models = [
                            Tag.get_or_create(name=name)[0] for name in tag_names
                        ]
                        note.tags.add(tag_models)
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to insert note: {exc}") from exc

        return note

    def list_notes(
        self, limit: int = 10, *, tags: Iterable[str] | None = None
    ) -> list[Note]:
        if limit <= 0:
            return []

        tag_names = _prepare_tags(tags)
        with self._connection():
            query = Note.select().order_by(Note.updated_at.desc())
            if tag_names:
                query = self._apply_tag_filter(query, tag_names)
            query = query.limit(int(limit))
            return list(query)

    def fetch_note(self, note_id: int) -> Note:
        with self._connection():
            try:
                return Note.get_by_id(int(note_id))
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
        tags: Iterable[str] | None = None,
        extra_data: ExtraData | object = _UNSET,
    ) -> Note:
        normalized_title = title.strip()
        normalized_body = body.rstrip()
        if not (normalized_title or normalized_body):
            raise StorageError("Cannot update note with empty content.")

        new_updated = _coerce_utc(updated_at)
        new_created = _coerce_utc(created_at) if created_at is not None else None
        tag_names = _prepare_tags(tags) if tags is not None else None

        with self._connection():
            try:
                with self._database.atomic():
                    note = Note.get_by_id(int(note_id))

                    note.title = normalized_title
                    note.body = normalized_body
                    note.description = description
                    note.updated_at = new_updated
                    if new_created is not None:
                        note.created_at = new_created
                    if can_publish is not None:
                        note.can_publish = can_publish
                    if extra_data is not _UNSET:
                        note.extra_data = self._dump_extra_data(extra_data)

                    note.save()

                    if tag_names is not None:
                        tag_models = [
                            Tag.get_or_create(name=name)[0] for name in tag_names
                        ]
                        note.tags.clear()
                        if tag_models:
                            note.tags.add(tag_models)
            except DoesNotExist:
                raise StorageError(f"Note '{note_id}' not found.") from None
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to update note: {exc}") from exc

        return note

    def fetch_last_updated_note(self) -> Note:
        with self._connection():
            note = Note.select().order_by(Note.updated_at.desc()).limit(1).first()
            if note is None:
                raise StorageError("No notes available.")
            return note

    def count_notes(self) -> int:
        with self._connection():
            return Note.select().count()

    def list_tags(self) -> list[str]:
        """Return all tag names sorted alphabetically."""

        with self._connection():
            query = Tag.select(Tag.name).order_by(Tag.name.asc())
            return [tag.name for tag in query]

    def delete_note(self, note_id: int) -> None:
        with self._connection():
            try:
                with self._database.atomic():
                    note = Note.get_by_id(int(note_id))
                    note.tags.clear()
                    note.delete_instance()
            except DoesNotExist:
                raise StorageError(f"Note '{note_id}' not found.") from None
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to delete note: {exc}") from exc

    def snapshot_notes(self) -> list["NoteSnapshot"]:
        """Return all notes with tags for export scenarios."""

        snapshots: list[NoteSnapshot] = []
        with self._connection():
            query = Note.select().order_by(Note.updated_at.desc())
            prefetched = prefetch(query, self._through_model, Tag)
            for note in prefetched:
                tag_names = sorted({tag.name for tag in note.tags})
                snapshots.append(
                    NoteSnapshot(
                        id=note.id,
                        title=note.title,
                        body=note.body,
                        description=note.description,
                        created_at=note.created_at,
                        updated_at=note.updated_at,
                        can_publish=bool(note.can_publish),
                        tags=tag_names,
                        extra_data=self._load_extra_data(note.extra_data),
                    )
                )
        return snapshots

    def search_notes(
        self,
        pattern: str,
        *,
        tags: Iterable[str] | None = None,
    ) -> list[Note]:
        text = str(pattern)
        if not text:
            return []

        lowered = text.lower()
        tag_names = _prepare_tags(tags)

        with self._connection():
            query = (
                Note.select()
                .where(
                    (fn.LOWER(Note.title).contains(lowered))
                    | (fn.LOWER(Note.body).contains(lowered))
                    | (fn.LOWER(Note.description).contains(lowered))
                )
                .order_by(Note.updated_at.desc())
            )
            if tag_names:
                query = self._apply_tag_filter(query, tag_names)
            return list(query)

    def prune_unused_tags(self) -> "PruneResult":
        """Remove tag associations that point to missing rows and drop orphan tags."""

        through_table = self._through_model._meta.table_name

        with self._connection():
            try:
                with self._database.atomic():
                    orphan_links_cursor = self._database.execute_sql(
                        (
                            f"DELETE FROM {through_table} "
                            f"WHERE note_id NOT IN (SELECT id FROM {TABLE_NOTES}) "
                            f"   OR tag_id NOT IN (SELECT id FROM {TABLE_TAGS})"
                        )
                    )
                    removed_links = max(orphan_links_cursor.rowcount or 0, 0)

                    orphan_tags_cursor = self._database.execute_sql(
                        (
                            f"DELETE FROM {TABLE_TAGS} "
                            f"WHERE NOT EXISTS ("
                            f"    SELECT 1 FROM {through_table} "
                            f"    WHERE {through_table}.tag_id = {TABLE_TAGS}.id"
                            f")"
                        )
                    )
                    removed_tags = max(orphan_tags_cursor.rowcount or 0, 0)
            except Exception as exc:  # pragma: no cover - defensive
                raise StorageError(f"Failed to prune tags: {exc}") from exc

        return PruneResult(removed_links=removed_links, removed_tags=removed_tags)

    @contextmanager
    def _connection(self):
        with self._database.connection_context():
            yield

    def _apply_tag_filter(self, query, tag_names: list[str]):
        through = self._through_model
        tag_count = len(tag_names)
        return (
            query.join(through, on=(through.note == Note.id))
            .join(Tag)
            .where(Tag.name.in_(tag_names))
            .group_by(Note.id)
            .having(fn.COUNT(fn.DISTINCT(Tag.id)) == tag_count)
        )

    def _ensure_extra_data_column(self) -> None:
        info = self._database.execute_sql(
            f"PRAGMA table_info({TABLE_NOTES})"
        ).fetchall()
        has_column = any(row[1] == "extra_data" for row in info)
        if not has_column:
            self._database.execute_sql(
                f"ALTER TABLE {TABLE_NOTES} ADD COLUMN extra_data TEXT"
            )

    @staticmethod
    def _dump_extra_data(data: ExtraData) -> str | None:
        if not data:
            return None
        try:
            return json.dumps(data)
        except TypeError as exc:  # pragma: no cover - defensive
            raise StorageError(f"Failed to serialize extra data: {exc}") from exc

    @staticmethod
    def _load_extra_data(raw: str | None) -> ExtraData:
        if raw is None:
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None


@dataclass(slots=True)
class PruneResult:
    """Report counts for storage pruning operations."""

    removed_links: int
    removed_tags: int


@dataclass(slots=True)
class NoteSnapshot:
    """Detached representation of a note with tags for export flows."""

    id: int
    title: str
    body: str
    description: str
    created_at: datetime
    updated_at: datetime
    can_publish: bool
    tags: list[str]
    extra_data: ExtraData
