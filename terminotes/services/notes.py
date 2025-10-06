"""High-level note workflows used by the CLI."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

import httpx

from ..app import AppContext
from ..editor import open_editor as default_open_editor
from ..notes_frontmatter import parse_document, render_document
from ..storage import Note
from ..utils.datetime_fmt import (
    now_user_friendly_local,
    parse_user_datetime,
    to_user_friendly_local,
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


class _TitleParser(HTMLParser):
    """HTML parser that captures the first <title> element."""

    def __init__(self) -> None:
        super().__init__()
        self._record = False
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() == "title" and self.title is None:
            self._record = True

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag.lower() == "title":
            self._record = False

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._record and self.title is None:
            candidate = data.strip()
            if candidate:
                self.title = candidate


def get_page_title(url: str, *, timeout: float = 5.0) -> str | None:
    """Fetch the page for ``url`` and return the first <title> string."""

    target = url.strip()
    if not target:
        return None

    try:
        response = httpx.get(
            target,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "terminotes-link-preview/0.1 (+https://github.com/jcapul/terminotes)",
            },
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return None

    parser = _TitleParser()
    try:
        parser.feed(response.text)
    except Exception:  # pragma: no cover - defensive against malformed HTML
        return None
    return parser.title


def _hostname_from_url(url: str, *, max_len: int = MAX_TITLE_CHARS) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or url
    if len(host) <= max_len:
        return host
    return host[: max_len - 1].rstrip(" -.") + "\u2026"


def create_log_entry(
    ctx: AppContext,
    body: str,
    *,
    created_at: datetime | None = None,
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
        created_at=created_at,
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
    created_at: datetime | None = None,
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

    wayback_url = snapshot["url"] if snapshot else None

    extra_data = {
        "link": {
            "source_url": source_url,
            "wayback": wayback_url,
        }
    }

    page_title = get_page_title(source_url)
    title = page_title or _derive_title_from_body(comment_text)
    if title:
        title = title + f" ({_hostname_from_url(source_url)})"
    else:
        title = source_url

    link_tags = ["link"] + list(tags or [])

    note = ctx.storage.create_note(
        title=title,
        body=comment_text,
        can_publish=False,
        created_at=created_at,
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

    timestamp = now_user_friendly_local()
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
    has_extra_data, extra_data_payload = _extract_extra_data(parsed.metadata, warn=warn)

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        parsed.metadata.get("last_edited"), field="last_edited", warn=warn
    )

    create_kwargs: dict[str, Any] = {}
    if has_extra_data:
        create_kwargs["extra_data"] = extra_data_payload

    note = ctx.storage.create_note(
        parsed.title or "",
        parsed.body,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=can_publish_flag,
        tags=note_tags,
        **create_kwargs,
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
        "date": to_user_friendly_local(existing.created_at),
        "last_edited": to_user_friendly_local(existing.updated_at),
        "can_publish": existing.can_publish,
        "tags": sorted(tag.name for tag in existing.tags),
    }

    original_last_edited_value = meta["last_edited"]

    decoded_extra = _decode_extra_data(existing.extra_data)
    if decoded_extra is not None:
        meta["extra_data"] = decoded_extra

    template = render_document(
        title=str(meta["title"]), body=existing.body, metadata=meta
    )  # type: ignore[arg-type]
    raw = ef(template, editor=ctx.config.editor)
    parsed = parse_document(raw)

    raw_last_edited_value = parsed.metadata.get("last_edited")

    created_at_dt = _parse_optional_dt(
        parsed.metadata.get("date"), field="date", warn=warn
    )
    updated_at_dt = _parse_optional_dt(
        raw_last_edited_value, field="last_edited", warn=warn
    )

    if _should_auto_update_last_edited(
        original_last_edited_value, raw_last_edited_value, updated_at_dt
    ):
        updated_at_dt = None

    new_can_publish = _extract_can_publish(
        parsed.metadata, default=existing.can_publish
    )
    new_tags = _extract_tags(parsed.metadata)
    has_extra_data, extra_data_payload = _extract_extra_data(parsed.metadata, warn=warn)

    update_kwargs: dict[str, Any] = {}
    if has_extra_data:
        update_kwargs["extra_data"] = extra_data_payload

    updated = ctx.storage.update_note(
        target_id,
        parsed.title or "",
        parsed.body,
        parsed.description,
        created_at=created_at_dt,
        updated_at=updated_at_dt,
        can_publish=new_can_publish,
        tags=new_tags,
        **update_kwargs,
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


def _decode_extra_data(raw: object) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
    if isinstance(raw, dict):
        return raw
    return None


def _extract_extra_data(
    metadata: dict[str, object], *, warn: WarnFunc | None
) -> tuple[bool, dict[str, Any] | None]:
    if "extra_data" not in metadata:
        return False, None
    value = metadata["extra_data"]
    if value is None:
        return True, None
    if isinstance(value, dict):
        return True, value
    if warn is not None:
        warn("Warning: Ignoring invalid 'extra_data' metadata; expected a mapping.")
    return False, None


def _should_auto_update_last_edited(
    original_value: object,
    candidate_value: object,
    parsed_candidate: datetime | None,
) -> bool:
    if candidate_value is None:
        return True
    if isinstance(candidate_value, str) and not candidate_value.strip():
        return True
    if parsed_candidate is None:
        return True
    original_dt = _coerce_metadata_datetime(original_value)
    if original_dt is not None and parsed_candidate == original_dt:
        return True
    return False


def _coerce_metadata_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return parse_user_datetime(text)
        except Exception:
            return None
    return None
