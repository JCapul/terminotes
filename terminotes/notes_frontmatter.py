"""Front matter rendering and parsing for editor payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import yaml

FRONTMATTER_DELIM = "---"


@dataclass(slots=True)
class ParsedEditorNote:
    """Outcome of parsing the editor payload."""

    title: str | None
    body: str
    description: str
    tags: tuple[str, ...]
    metadata: dict[str, Any]


def render_document(title: str, body: str, metadata: dict[str, Any]) -> str:
    payload = yaml.safe_dump(metadata, sort_keys=False).strip()
    body_block = body.rstrip()
    if body_block:
        return f"{FRONTMATTER_DELIM}\n{payload}\n{FRONTMATTER_DELIM}\n\n{body_block}\n"
    return f"{FRONTMATTER_DELIM}\n{payload}\n{FRONTMATTER_DELIM}\n\n"


def parse_document(raw: str) -> ParsedEditorNote:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, tags=(), metadata={})

    try:
        closing_index = lines.index(FRONTMATTER_DELIM, 1)
    except ValueError:
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, tags=(), metadata={})

    metadata_block = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).strip()

    metadata: dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(metadata_block) or {}
        if isinstance(loaded, dict):
            metadata = loaded
    except yaml.YAMLError:
        metadata = {}

    title: str | None = None
    title_value = metadata.get("title")
    if isinstance(title_value, str):
        title = title_value.strip() or None

    description_value = metadata.get("description")
    description = ""
    if isinstance(description_value, str):
        description = description_value.strip()

    tags_value = metadata.get("tags")
    tags: tuple[str, ...]
    if isinstance(tags_value, str):
        tags_iter = [part.strip() for part in tags_value.split(",") if part.strip()]
        tags = tuple(tags_iter)
    elif isinstance(tags_value, Iterable) and not isinstance(tags_value, (str, bytes)):
        tags = tuple(str(tag).strip() for tag in tags_value if str(tag).strip())
    else:
        tags = ()

    return ParsedEditorNote(
        title=title, body=body, description=description, tags=tags, metadata=metadata
    )
