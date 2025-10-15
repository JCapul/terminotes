"""Pluggy integration for the built-in Markdown exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from terminotes.config import TerminotesConfig
from terminotes.plugins import ExportContribution, hookimpl
from terminotes.storage import Storage

from .config import PLUGIN_ID, resolve_plugin_config
from .exporter import export_markdown


@hookimpl
def bootstrap(config: TerminotesConfig) -> None:  # pragma: no cover - nothing to setup
    """Markdown plugin currently has no bootstrap requirements."""

    resolve_plugin_config(config)


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in Markdown exporter as a plugin contribution."""

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


__all__ = ["PLUGIN_ID", "bootstrap", "export_formats"]
