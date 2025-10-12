"""Export services for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..exporters import ExportError
from ..plugins import ExportContribution, PluginRegistrationError
from ..plugins.runtime import load_export_contributions, reset_plugin_manager_cache
from ..storage import Storage


@dataclass(frozen=True)
class ExportRegistry:
    """Aggregated exporter contributions discovered at runtime."""

    contributions: dict[str, ExportContribution]


@lru_cache(maxsize=1)
def _load_export_registry() -> ExportRegistry:
    contributions = load_export_contributions()
    return ExportRegistry(contributions=contributions)


def clear_export_registry_cache() -> None:
    """Reset cached exporter discovery (primarily for testing)."""

    _load_export_registry.cache_clear()
    reset_plugin_manager_cache()


def get_export_format_choices() -> list[str]:
    """Return the list of available export format identifiers."""

    registry = _load_export_registry()
    return sorted(registry.contributions.keys())


def get_export_format_descriptions() -> list[tuple[str, str]]:
    """Return tuples of ``(format_id, description)`` for available exporters."""

    registry = _load_export_registry()
    return sorted(
        ((fmt, contrib.description) for fmt, contrib in registry.contributions.items()),
        key=lambda item: item[0],
    )


def export_notes(
    storage: Storage,
    *,
    export_format: str,
    destination: Path,
) -> int:
    """Export all notes from storage to the given target format."""

    try:
        registry = _load_export_registry()
    except PluginRegistrationError as exc:  # pragma: no cover - defensive
        raise ExportError(str(exc)) from exc

    formats = registry.contributions
    format_lower = export_format.lower()

    contribution = formats.get(format_lower)
    if contribution is None:
        available = ", ".join(sorted(formats))
        if available:
            raise ExportError(
                f"Unknown export format: {export_format}. Available: {available}."
            )
        raise ExportError("No export plugins are available.")

    try:
        return contribution.formatter(
            storage=storage,
            destination=destination,
            options=None,
        )
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(
            f"Exporter '{contribution.format_id}' raised an unexpected error: {exc}"
        ) from exc
