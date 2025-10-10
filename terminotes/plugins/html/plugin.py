"""Pluggy integration for the built-in HTML exporter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from terminotes.config import DEFAULT_CONFIG_DIR
from terminotes.exporters import ExportError
from terminotes.plugins import BootstrapContext, ExportContribution, hookimpl
from terminotes.storage import NoteSnapshot, Storage

from .config import (
    DEFAULT_SITE_TITLE,
    PLUGIN_ID,
    HtmlPluginConfig,
    ensure_templates,
    resolve_plugin_config,
    templates_dir_from,
)
from .exporter import HtmlExporter

_current_config = HtmlPluginConfig(
    site_title=DEFAULT_SITE_TITLE,
    templates_root=DEFAULT_CONFIG_DIR,
)


def _collect_notes(storage: Storage) -> list[NoteSnapshot]:
    return storage.snapshot_notes()


def _export_html(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    exporter = HtmlExporter(
        templates_dir_from(_current_config),
        site_title=_current_config.site_title,
    )
    try:
        return exporter.export(_collect_notes(storage), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"HTML export failed: {exc}") from exc


@hookimpl
def bootstrap(context: BootstrapContext) -> None:
    """Capture configuration and ensure templates before exporters run."""

    global _current_config
    plugin_config = resolve_plugin_config(context)
    ensure_templates(plugin_config.templates_root)
    _current_config = plugin_config


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in HTML exporter as a plugin contribution."""

    contribution = ExportContribution(
        format_id="html",
        formatter=_export_html,
        description="Static HTML site with search",
    )
    return (contribution,)


__all__ = ["PLUGIN_ID", "bootstrap", "export_formats"]
