"""Export services for Terminotes."""

from __future__ import annotations

from pathlib import Path

from ..config import DEFAULT_CONFIG_DIR, TEMPLATE_RELATIVE_DIR
from ..exporters import ExportError, HtmlExporter, MarkdownExporter
from ..storage import Storage


def export_notes(
    storage: Storage,
    *,
    export_format: str,
    destination: Path,
    site_title: str | None = None,
    templates_root: Path | None = None,
) -> int:
    """Export all notes from storage to the given target format."""

    notes = storage.snapshot_notes()
    dest = destination
    format_lower = export_format.lower()

    if format_lower == "html":
        templates_dir = (templates_root or DEFAULT_CONFIG_DIR) / TEMPLATE_RELATIVE_DIR
        exporter = HtmlExporter(templates_dir, site_title=site_title or "Terminotes")
        return exporter.export(notes, dest)

    if format_lower == "markdown":
        exporter = MarkdownExporter()
        return exporter.export(notes, dest)

    raise ExportError(f"Unknown export format: {export_format}")
