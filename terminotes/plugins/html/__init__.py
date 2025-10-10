"""Built-in HTML exporter plugin for Terminotes."""

from __future__ import annotations

from .config import (
    DEFAULT_SITE_TITLE,
    PLUGIN_ID,
    HtmlPluginConfig,
    ensure_templates,
    resolve_plugin_config,
    templates_dir_from,
)
from .exporter import HtmlExporter
from .plugin import bootstrap, export_formats

__all__ = [
    "DEFAULT_SITE_TITLE",
    "HtmlExporter",
    "HtmlPluginConfig",
    "PLUGIN_ID",
    "bootstrap",
    "ensure_templates",
    "export_formats",
    "resolve_plugin_config",
    "templates_dir_from",
]
