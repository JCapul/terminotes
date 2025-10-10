"""Markdown export implementation for the built-in Terminotes plugin."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from terminotes.exporters import ExportError
from terminotes.storage import NoteSnapshot, Storage


def _slugify(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return "note"
    slug = re.sub(r"[^a-z0-9]+", "-", value)
    slug = slug.strip("-")
    return slug or "note"


class MarkdownExporter:
    """Render notes into individual Markdown files with YAML front matter."""

    def export(self, notes: list[NoteSnapshot], destination: Path) -> int:
        dest = destination
        dest.mkdir(parents=True, exist_ok=True)

        count = 0
        for note in notes:
            count += 1
            slug = _slugify(note.title or f"note-{note.id}")
            filename = f"{note.id:04d}-{slug}.md"
            file_path = dest / filename

            metadata: dict[str, Any] = {
                "id": note.id,
                "title": note.title or "",
                "description": note.description or "",
                "date": note.created_at.isoformat(),
                "last_edited": note.updated_at.isoformat(),
                "can_publish": bool(note.can_publish),
                "tags": note.tags,
            }

            if note.extra_data is not None:
                metadata["extra_data"] = note.extra_data

            yaml_text = yaml.safe_dump(
                metadata,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).strip()

            front_matter = f"---\n{yaml_text}\n---\n\n"
            body = (note.body or "").rstrip() + "\n"
            file_path.write_text(front_matter + body, encoding="utf-8")

        return count


def export_markdown(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    _ = options  # markdown exporter currently ignores additional options
    exporter = MarkdownExporter()
    try:
        return exporter.export(storage.snapshot_notes(), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"Markdown export failed: {exc}") from exc


__all__ = ["MarkdownExporter", "export_markdown"]
