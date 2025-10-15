"""Hook specifications for Terminotes plugins."""

from __future__ import annotations

from collections.abc import Iterable

from terminotes.config import TerminotesConfig

from ._markers import hookspec
from .types import ExportContribution


class TerminotesHookSpec:
    """Collection of pluggy hook specifications."""

    @hookspec
    def bootstrap(self, config: TerminotesConfig) -> None:
        """Run setup tasks during Terminotes bootstrap."""

    @hookspec
    def export_formats(self) -> Iterable[ExportContribution]:
        """Return exporter contributions (format handlers) provided by the plugin."""
