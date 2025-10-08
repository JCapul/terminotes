"""Export services for Terminotes."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..exporters import ExportError
from ..plugins import (
    ExportContribution,
    PluginLoadError,
    PluginRegistrationError,
    create_plugin_manager,
    get_load_errors,
    iter_export_contributions,
    register_modules,
)
from ..storage import Storage


@dataclass(frozen=True)
class ExportRegistry:
    """Aggregated exporter contributions discovered at runtime."""

    contributions: dict[str, ExportContribution]
    load_errors: tuple[PluginLoadError, ...]


def _iter_plugin_modules() -> tuple[object, ...]:
    from ..plugins.builtin import BUILTIN_PLUGINS

    return BUILTIN_PLUGINS


@lru_cache(maxsize=1)
def _load_export_registry() -> ExportRegistry:
    manager = create_plugin_manager()
    register_modules(manager, _iter_plugin_modules())

    contributions: dict[str, ExportContribution] = {}
    for contribution in iter_export_contributions(manager):
        key = contribution.format_id.lower()
        if key in contributions:
            raise PluginRegistrationError(
                f"Duplicate export format detected: '{contribution.format_id}'."
            )
        contributions[key] = contribution

    load_errors = tuple(get_load_errors(manager))
    return ExportRegistry(contributions=contributions, load_errors=load_errors)


def clear_export_registry_cache() -> None:
    """Reset cached exporter discovery (primarily for testing)."""

    _load_export_registry.cache_clear()


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
    site_title: str | None = None,
    templates_root: Path | None = None,
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
        load_hint = ""
        if registry.load_errors:
            failed = ", ".join(error.name for error in registry.load_errors)
            load_hint = f" (plugins failed to load: {failed})"
        if available:
            message = f"Unknown export format: {export_format}. Available: {available}."
            if load_hint:
                message += load_hint
            raise ExportError(message)
        raise ExportError("No export plugins are available." + load_hint)

    options: dict[str, object] = {}
    if site_title is not None:
        options["site_title"] = site_title
    if templates_root is not None:
        options["templates_root"] = templates_root

    try:
        return contribution.formatter(
            storage=storage,
            destination=destination,
            options=options or None,
        )
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(
            f"Exporter '{contribution.format_id}' raised an unexpected error: {exc}"
        ) from exc
