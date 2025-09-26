"""High-level note workflows used by the CLI."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable, Iterable
from urllib.parse import urlparse

from ..app import AppContext
from ..editor import open_editor as default_open_editor
from ..notes_frontmatter import parse_document, render_document
from ..storage import Note
from ..utils.datetime_fmt import (
    now_user_friendly_utc,
    parse_user_datetime,
    to_user_friendly_utc,
)
from ..utils.wayback import fetch_latest_snapshot

WarnFunc = Callable[[str], None]
EditFunc = Callable[[str, str | None], str]

MAX_TITLE_CHARS = 80


def _derive_title_from_body(body: str, *, max_len: int = MAX_TITLE_CHARS) -> str:
    """Derive a title from the body text.

    Preference order:
    1) Initial sentence ending with '.', '!' or '?'
    2) Otherwise, the first line

    The result is trimmed and truncated to ``max_len`` characters,
    appending an ellipsis when truncated.
    """
    text = body.strip()
    if not text:
        return ""

    # Try to capture the first sentence ending with a sentence mark.
    m = re.search(r"^\s*(.+?[\.\!\?])(?:\s|$)", text, flags=re.S)
    if m:
        candidate = m.group(1).strip()
    else:
        # Fallback: first line
        candidate = text.splitlines()[0].strip()

    if len(candidate) <= max_len:
        return candidate
    # Truncate and add ellipsis
    return candidate[: max_len - 1].rstrip() + "\u2026"


def _title_from_url(url: str, *, max_len: int = MAX_TITLE_CHARS) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or url
    if len(host) <= max_len:
        return host
    return host[: max_len - 1].rstrip(" -.") + "\u2026"


def create_log_entry(
    ctx: AppContext,
    body: str,
    *,
    warn: WarnFunc | None = None,
    tags: Iterable[str] | None = None,
) -> Note:
    """Create a new log-type note directly (no editor)."""

    title = _derive_title_from_body(body)

    note = ctx.storage.create_note(
        title=title,
        body=body,
        description="",
        can_publish=False,
        tags=list(tags) if tags is not None else None,
    )
    # Commit the DB update locally (no network interaction).
    ctx.git_sync.commit_db_update(ctx.storage.path, f"chore(db): create log {note.id}")
    return note


def create_link_entry(
    ctx: AppContext,
    url: str,
    comment: str = "",
    *,
    warn: WarnFunc | None = None,
    tags: Iterable[str] | None = None,
) -> tuple[Note, dict[str, str] | None]:
    """Create a note representing a saved link with optional comment."""

    source_url = url.strip()
    if not source_url:
        raise ValueError("A URL is required to create a link note.")

    comment_text = comment.strip()

    snapshot = fetch_latest_snapshot(source_url)
    if snapshot is None and warn is not None:
        warn("No Wayback snapshot found for the provided URL.")

    extra_data = {
        "link": {
            "source_url": source_url,
            "wayback": snapshot,
        }
    }

    body_lines: list[str] = []
    if comment_text:
        body_lines.append(comment_text)
        body_lines.append("")
    body_lines.append(source_url)
    if snapshot is not None:
        body_lines.append("")
        body_lines.append(f"Wayback fallback: {snapshot['url']}")
        timestamp = snapshot.get("timestamp")
        if timestamp:
            body_lines.append(f"Snapshot captured: {timestamp}")

    body = "\n".join(body_lines)

    title = comment_text or _title_from_url(source_url)
    description = comment_text

    link_tags = ["link"] + list(tags or [])

    note = ctx.storage.create_note(
        title=title,
        body=body,
        description=description,
        can_publish=False,
        tags=link_tags,
        extra_data=extra_data,
    )
    ctx.git_sync.commit_db_update(ctx.storage.path, f"chore(db): create link {note.id}")
    return note, snapshot


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
        "tags": [],
    }

    template = render_document(title="", body="", metadata=metadata)
    raw = ef(template, editor=ctx.config.editor)
    parsed = parse_document(raw)

    can_publish_flag = _extract_can_publish(parsed.metadata, default=False)
    note_tags = _extract_tags(parsed.metadata)

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        parsed.metadata.get("last_edited"), field="last_edited", warn=warn
    )

    note = ctx.storage.create_note(
        parsed.title or "",
        parsed.body,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=can_publish_flag,
        tags=note_tags,
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
        "tags": sorted(tag.name for tag in existing.tags),
    }

    template = render_document(
        title=str(meta["title"]), body=existing.body, metadata=meta
    )  # type: ignore[arg-type]
    raw = ef(template, editor=ctx.config.editor)
    parsed = parse_document(raw)

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        parsed.metadata.get("last_edited"), field="last_edited", warn=warn
    )

    new_can_publish = _extract_can_publish(
        parsed.metadata, default=existing.can_publish
    )
    new_tags = _extract_tags(parsed.metadata)

    updated = ctx.storage.update_note(
        target_id,
        parsed.title or "",
        parsed.body,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=new_can_publish,
        tags=new_tags,
    )
    # Commit the DB update locally (no network interaction).
    ctx.git_sync.commit_db_update(
        ctx.storage.path, f"chore(db): update note {updated.id}"
    )
    return updated


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


def _extract_tags(metadata: dict[str, object]) -> list[str]:
    value = metadata.get("tags")
    if isinstance(value, str):
        name = value.strip()
        return [name] if name else []
    if isinstance(value, Iterable):
        tags: list[str] = []
        for item in value:
            name = str(item).strip()
            if not name or name in tags:
                continue
            tags.append(name)
        return tags
    return []
