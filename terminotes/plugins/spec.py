"""Hook specifications for Terminotes plugins."""

from __future__ import annotations

from collections.abc import Iterable

from terminotes.config import TerminotesConfig

from ._markers import hookspec
from .types import ExportContribution


class TerminotesHookSpec:
    """Collection of pluggy hook specifications."""

    @hookspec
    def export_formats(self, config: TerminotesConfig) -> Iterable[ExportContribution]:
        """Return exporter contributions (format handlers) provided by the plugin."""
