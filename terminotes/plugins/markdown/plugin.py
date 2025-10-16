"""Pluggy integration for the built-in Markdown exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from terminotes.config import TerminotesConfig
from terminotes.plugins import ExportContribution, hookimpl
from terminotes.storage import Storage

from .exporter import export_markdown

PLUGIN_ID = "terminotes-builtin-markdown"


@hookimpl
def export_formats(config: TerminotesConfig) -> tuple[ExportContribution, ...]:
    """Expose the built-in Markdown exporter as a plugin contribution."""

    # Touch plugin configuration to highlight where settings would be consumed.
    config.plugins.get(PLUGIN_ID, {})

    contribution = ExportContribution(
        format_id="markdown",
        formatter=_export_markdown,
        description="Markdown files with YAML front matter",
    )
    return (contribution,)


def _export_markdown(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, object] | None = None,
) -> int:
    return export_markdown(
        storage=storage,
        destination=destination,
        options=options,
    )


__all__ = ["PLUGIN_ID", "export_formats"]
