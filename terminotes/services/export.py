"""Export services for Terminotes."""

from __future__ import annotations

from pathlib import Path

from ..config import TerminotesConfig
from ..plugins import (
    ExportContribution,
    PluginRegistrationError,
    load_export_contributions,
    reset_plugin_manager_cache,
)
from ..storage import Storage


class ExportError(RuntimeError):
    """Raised when exporting notes fails."""


def clear_export_registry_cache() -> None:
    """Reset cached exporter discovery (primarily for testing)."""

    reset_plugin_manager_cache()


def _load_export_registry(config: TerminotesConfig) -> dict[str, ExportContribution]:
    try:
        return load_export_contributions(config)
    except PluginRegistrationError as exc:  # pragma: no cover - defensive
        raise ExportError(str(exc)) from exc


def get_export_format_choices(config: TerminotesConfig) -> list[str]:
    """Return the list of available export format identifiers."""

    registry = _load_export_registry(config)
    return sorted(registry.keys())


def get_export_format_descriptions(
    config: TerminotesConfig,
) -> list[tuple[str, str]]:
    """Return tuples of ``(format_id, description)`` for available exporters."""

    registry = _load_export_registry(config)
    return sorted(
        ((fmt, contrib.description) for fmt, contrib in registry.items()),
        key=lambda item: item[0],
    )


def export_notes(
    config: TerminotesConfig,
    storage: Storage,
    *,
    export_format: str,
    destination: Path,
) -> int:
    """Export all notes from storage to the given target format."""

    formats = _load_export_registry(config)
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
