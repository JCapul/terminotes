"""Built-in HTML exporter plugin for Terminotes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ...config import DEFAULT_CONFIG_DIR, TEMPLATE_RELATIVE_DIR
from ...exporters import ExportError, HtmlExporter
from ...storage import Storage
from .. import ExportContribution, hookimpl


def _resolve_site_title(options: Mapping[str, Any] | None) -> str:
    if not options:
        return "Terminotes"
    value = options.get("site_title")
    if value is None:
        return "Terminotes"
    return str(value)


def _resolve_templates_root(options: Mapping[str, Any] | None) -> Path:
    if not options:
        return DEFAULT_CONFIG_DIR
    root = options.get("templates_root")
    if root is None:
        return DEFAULT_CONFIG_DIR
    if isinstance(root, Path):
        return root
    return Path(root)


def _export_html(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    site_title = _resolve_site_title(options)
    templates_root = _resolve_templates_root(options)
    templates_dir = templates_root / TEMPLATE_RELATIVE_DIR

    exporter = HtmlExporter(templates_dir, site_title=site_title)
    try:
        return exporter.export(storage.snapshot_notes(), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"HTML export failed: {exc}") from exc


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in HTML exporter as a plugin contribution."""

    contribution = ExportContribution(
        format_id="html",
        formatter=_export_html,
        description="Static HTML site with search",
    )
    return (contribution,)
