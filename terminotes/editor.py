"""Utilities for launching an editor to capture note content."""

from __future__ import annotations

import click


class EditorError(RuntimeError):
    """Raised when the external editor fails or returns no note content."""


def open_editor(initial_content: str = "", editor: str | None = None) -> str:
    """Launch the configured editor using Click and return captured content."""

    try:
        content = click.edit(text=initial_content, editor=editor, extension=".md")
    except OSError as exc:  # pragma: no cover - depends on system configuration
        raise EditorError(f"Failed to launch editor '{editor or ''}': {exc}") from exc

    if content is None:
        raise EditorError("Note capture aborted: editor closed without saving.")

    content = content.strip()
    if not content:
        raise EditorError("Note capture aborted: editor returned empty content.")

    return content
