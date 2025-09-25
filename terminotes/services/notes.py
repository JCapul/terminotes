"""High-level note workflows used by the CLI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable

from ..app import AppContext
from ..editor import open_editor as default_open_editor
from ..notes_frontmatter import parse_document, render_document
from ..storage import Note
from ..utils.datetime_fmt import (
    now_user_friendly_utc,
    parse_user_datetime,
    to_user_friendly_utc,
)
from ..utils.tags import extract_hashtags

WarnFunc = Callable[[str], None]
EditFunc = Callable[[str, str | None], str]


def create_log_entry(
    ctx: AppContext,
    body: str,
    *,
    warn: WarnFunc | None = None,
) -> Note:
    """Create a new log-type note directly (no editor)."""

    final_tags = extract_hashtags(body)

    note = ctx.storage.create_note(
        title="",
        body=body,
        tags=final_tags,
        description="",
        can_publish=False,
    )
    # Commit the DB update locally (no network interaction).
    ctx.git_sync.commit_db_update(ctx.storage.path, f"chore(db): create log {note.id}")
    return note


def create_via_editor(
    ctx: AppContext,
    *,
    edit_fn: EditFunc | None = None,
    warn: WarnFunc | None = None,
) -> Note:
    """Open the editor with a template, persist a new note, and return it."""

    ef = edit_fn or default_open_editor

    timestamp = now_user_friendly_utc()
    metadata = {
        "title": "",
        "description": "",
        "date": timestamp,
        "last_edited": timestamp,
        "can_publish": False,
    }

    template = render_document(title="", body="", metadata=metadata)
    raw = ef(template, editor=ctx.config.editor)
    parsed = parse_document(raw)

    final_tags = extract_hashtags(parsed.body)

    can_publish_flag = _extract_can_publish(parsed.metadata, default=False)

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        parsed.metadata.get("last_edited"), field="last_edited", warn=warn
    )

    note = ctx.storage.create_note(
        parsed.title or "",
        parsed.body,
        final_tags,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=can_publish_flag,
    )
    # Commit the DB update locally (no network interaction).
    ctx.git_sync.commit_db_update(ctx.storage.path, f"chore(db): create note {note.id}")
    return note


def update_via_editor(
    ctx: AppContext,
    note_id: int,
    *,
    edit_fn: EditFunc | None = None,
    warn: WarnFunc | None = None,
) -> Note:
    """Open the editor for an existing note and persist changes.

    If ``note_id`` is ``None``, the most recently updated note is chosen.
    Returns the updated Note.
    """

    ef = edit_fn or default_open_editor

    if note_id == -1:
        existing = ctx.storage.fetch_last_updated_note()
        target_id = existing.id
    else:
        existing = ctx.storage.fetch_note(note_id)
        target_id = note_id

    meta: dict[str, object] = {
        "title": existing.title or "",
        "description": existing.description,
        "date": to_user_friendly_utc(existing.created_at),
        "last_edited": to_user_friendly_utc(existing.updated_at),
        "can_publish": existing.can_publish,
    }
    if existing.tags:
        meta["tags"] = list(existing.tags)

    template = render_document(
        title=str(meta["title"]), body=existing.body, metadata=meta
    )  # type: ignore[arg-type]
    raw = ef(template, editor=ctx.config.editor)
    parsed = parse_document(raw)

    # Always derive tags from the edited body content
    final_tags = extract_hashtags(parsed.body)

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        parsed.metadata.get("last_edited"), field="last_edited", warn=warn
    )

    new_can_publish = _extract_can_publish(
        parsed.metadata, default=existing.can_publish
    )

    updated = ctx.storage.update_note(
        target_id,
        parsed.title or "",
        parsed.body,
        final_tags,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=new_can_publish,
    )
    # Commit the DB update locally (no network interaction).
    ctx.git_sync.commit_db_update(
        ctx.storage.path, f"chore(db): update note {updated.id}"
    )
    return updated


def _normalize_tags(tags: Iterable[str]) -> tuple[str, ...]:
    # Deprecated helper retained for safety; prefer extract_hashtags(body).
    return tuple(str(t).strip() for t in tags if str(t).strip())


def _parse_optional_dt(
    value: object, *, field: str, warn: WarnFunc | None
) -> datetime | None:
    # Direct datetime provided (PyYAML may parse ISO timestamps already)
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            return parse_user_datetime(value)
        except Exception:
            if warn is not None:
                warn(f"Warning: Ignoring invalid '{field}' timestamp: {value}")
    return None


def _extract_can_publish(metadata: dict[str, object], default: bool) -> bool:
    value = metadata.get("can_publish")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"true", "1", "yes", "on"}:
            return True
        if val in {"false", "0", "no", "off"}:
            return False
    return default


# 'type' metadata removed; no extraction required.
