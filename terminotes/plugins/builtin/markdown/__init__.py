"""Built-in Markdown exporter plugin for Terminotes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from ....exporters import ExportError
from ....plugins import BootstrapContext, ExportContribution, hookimpl
from ....storage import NoteSnapshot, Storage

PLUGIN_ID = "terminotes-builtin-markdown"


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

            metadata = {
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


def _collect_notes(storage: Storage) -> list[NoteSnapshot]:
    return storage.snapshot_notes()


def _export_markdown(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    exporter = MarkdownExporter()
    try:
        return exporter.export(_collect_notes(storage), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"Markdown export failed: {exc}") from exc


@hookimpl
def bootstrap(context: BootstrapContext) -> None:  # pragma: no cover - nothing to setup
    """Markdown plugin currently has no bootstrap requirements."""

    _ = context


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in Markdown exporter as a plugin contribution."""

    contribution = ExportContribution(
        format_id="markdown",
        formatter=_export_markdown,
        description="Markdown files with YAML front matter",
    )
    return (contribution,)


__all__ = [
    "MarkdownExporter",
    "PLUGIN_ID",
    "bootstrap",
    "export_formats",
]
