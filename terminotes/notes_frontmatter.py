"""Front matter rendering and parsing for editor payloads (YAML-based)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

FRONTMATTER_DELIM = "---"


@dataclass(slots=True)
class ParsedEditorNote:
    """Outcome of parsing the editor payload."""

    title: str | None
    body: str
    description: str
    metadata: dict[str, Any]


def render_document(title: str, body: str, metadata: dict[str, Any]) -> str:
    cleaned_metadata = {
        key: value for key, value in metadata.items() if value is not None
    }
    payload = yaml.safe_dump(
        cleaned_metadata,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    body_block = body.rstrip()
    front_matter = f"{FRONTMATTER_DELIM}\n{payload}\n{FRONTMATTER_DELIM}\n\n"
    if body_block:
        return f"{front_matter}{body_block}\n"
    return front_matter


def parse_document(raw: str) -> ParsedEditorNote:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, description="", metadata={})

    try:
        closing_index = lines.index(FRONTMATTER_DELIM, 1)
    except ValueError:
        stripped = raw.strip()
        return ParsedEditorNote(title=None, body=stripped, description="", metadata={})

    metadata_block = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).strip()

    metadata: dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(metadata_block)
        if isinstance(loaded, dict):
            metadata = loaded
    except Exception:
        metadata = {}

    title: str | None = None
    title_value = metadata.get("title")
    if isinstance(title_value, str):
        title = title_value.strip() or None

    description_value = metadata.get("description")
    description = ""
    if isinstance(description_value, str):
        description = description_value.strip()

    return ParsedEditorNote(
        title=title, body=body, description=description, metadata=metadata
    )
