"""Front matter rendering and parsing for editor payloads (TOML-based)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import Any, Iterable

FRONTMATTER_DELIM = "+++"


@dataclass(slots=True)
class ParsedEditorNote:
    """Outcome of parsing the editor payload."""

    title: str | None
    body: str
    description: str
    metadata: dict[str, Any]


def render_document(title: str, body: str, metadata: dict[str, Any]) -> str:
    payload = _toml_dump(metadata).strip()
    body_block = body.rstrip()
    if body_block:
        return f"{FRONTMATTER_DELIM}\n{payload}\n{FRONTMATTER_DELIM}\n\n{body_block}\n"
    return f"{FRONTMATTER_DELIM}\n{payload}\n{FRONTMATTER_DELIM}\n\n"


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
        loaded = tomllib.loads(metadata_block)
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


def _toml_dump(data: dict[str, Any]) -> str:
    """Minimal TOML renderer for flat key/value front matter.

    Supports str, numbers, booleans, and lists of strings.
    """

    def quote(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    parts: list[str] = []
    for key, value in data.items():
        if isinstance(value, str):
            parts.append(f"{key} = {quote(value)}")
        elif isinstance(value, bool):
            parts.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key} = {value}")
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            arr = ", ".join(quote(str(v)) for v in value)
            parts.append(f"{key} = [{arr}]")
        elif value is None:
            # Skip Nones
            continue
        else:
            # Fallback to string representation
            parts.append(f"{key} = {quote(str(value))}")
    return "\n".join(parts) + "\n"
