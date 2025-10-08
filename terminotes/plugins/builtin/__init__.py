"""Built-in Terminotes plugins."""

from __future__ import annotations

from . import html, markdown

BUILTIN_PLUGINS = (html, markdown)

__all__ = ["BUILTIN_PLUGINS"]
