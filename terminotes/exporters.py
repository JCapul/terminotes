"""Terminotes export error types."""

from __future__ import annotations


class ExportError(RuntimeError):
    """Raised when exporting notes fails."""


__all__ = ["ExportError"]
