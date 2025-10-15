"""Configuration helpers for the built-in Markdown exporter plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from terminotes.config import TerminotesConfig

PLUGIN_ID = "terminotes-builtin-markdown"


@dataclass(frozen=True)
class MarkdownPluginConfig:
    """Resolved configuration data for the Markdown exporter plugin."""

    pass


DEFAULT_CONFIG = MarkdownPluginConfig()


def resolve_plugin_config(config: "TerminotesConfig") -> MarkdownPluginConfig:
    """Convert configuration data into plugin configuration."""

    _ = config  # markdown exporter has no runtime configuration yet
    return DEFAULT_CONFIG


__all__ = [
    "DEFAULT_CONFIG",
    "MarkdownPluginConfig",
    "PLUGIN_ID",
    "resolve_plugin_config",
]
