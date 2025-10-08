"""Built-in Markdown exporter plugin for Terminotes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ...exporters import ExportError, MarkdownExporter
from ...storage import Storage
from .. import ExportContribution, hookimpl


def _export_markdown(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    exporter = MarkdownExporter()
    try:
        return exporter.export(storage.snapshot_notes(), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"Markdown export failed: {exc}") from exc


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in Markdown exporter as a plugin contribution."""

    contribution = ExportContribution(
        format_id="markdown",
        formatter=_export_markdown,
        description="Markdown files with YAML front matter",
    )
    return (contribution,)
