"""Built-in Markdown exporter plugin for Terminotes."""

from __future__ import annotations

from .config import (
    DEFAULT_CONFIG,
    PLUGIN_ID,
    MarkdownPluginConfig,
    resolve_plugin_config,
)
from .exporter import MarkdownExporter, export_markdown
from .plugin import bootstrap, export_formats

__all__ = [
    "DEFAULT_CONFIG",
    "MarkdownExporter",
    "MarkdownPluginConfig",
    "PLUGIN_ID",
    "bootstrap",
    "export_formats",
    "export_markdown",
    "resolve_plugin_config",
]
