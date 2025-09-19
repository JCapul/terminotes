"""Utilities for launching an editor to capture note content."""

from __future__ import annotations

DEFAULT_TEMPLATE = """---\ntitle: \ntags: []\n---\n\n"""


def open_editor(initial_content: str = DEFAULT_TEMPLATE) -> str:
    """Placeholder for opening the configured editor and returning note content."""
    raise NotImplementedError("Editor integration pending implementation.")
