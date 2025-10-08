"""Type definitions for Terminotes plugin contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Protocol

if TYPE_CHECKING:  # pragma: no cover - type check only
    from ..config import TerminotesConfig
    from ..storage import Storage


class ExportHandler(Protocol):
    """Callable responsible for exporting notes to a destination."""

    def __call__(
        self,
        *,
        storage: "Storage",
        destination: Path,
        options: Mapping[str, Any] | None = None,
    ) -> int:  # pragma: no cover - Protocol
        """Execute the export and return the number of notes written."""


@dataclass(slots=True, frozen=True)
class ExportContribution:
    """Descriptor describing an additional export format provided by a plugin."""

    format_id: str
    formatter: ExportHandler
    description: str


class PluginSettingsGetter(Protocol):
    """Callable returning plugin-specific configuration mappings."""

    def __call__(
        self,
        plugin_id: str,
        *,
        default: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:  # pragma: no cover - Protocol
        """Return the configuration for ``plugin_id`` or ``default`` when missing."""


@dataclass(slots=True, frozen=True)
class BootstrapContext:
    """Data passed to exporter plugins during Terminotes bootstrap."""

    config: "TerminotesConfig"
    get_settings: PluginSettingsGetter
