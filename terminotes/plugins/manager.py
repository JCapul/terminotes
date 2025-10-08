"""Helpers for creating and working with the Terminotes plugin manager."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from importlib import metadata

import pluggy

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE
from .spec import TerminotesHookSpec
from .types import BootstrapContext, ExportContribution


class PluginRegistrationError(RuntimeError):
    """Raised when a plugin fails validation or registration."""


@dataclass(slots=True, frozen=True)
class PluginLoadError:
    """Captures a failure while loading or registering a plugin entry point."""

    name: str
    value: str
    exception: Exception


def create_plugin_manager(*, load_entry_points: bool = True) -> pluggy.PluginManager:
    """Instantiate a pluggy ``PluginManager`` configured for Terminotes."""

    manager = pluggy.PluginManager(PLUGIN_NAMESPACE)
    manager.add_hookspecs(TerminotesHookSpec)

    setattr(manager, "_terminotes_load_errors", ())

    if load_entry_points:
        errors = load_plugin_entry_points(manager)
        setattr(manager, "_terminotes_load_errors", tuple(errors))

    return manager


def register_modules(
    manager: pluggy.PluginManager,
    modules: Sequence[object],
) -> None:
    """Register in-process plugin modules with the manager."""

    for module in modules:
        try:
            manager.register(module)
        except pluggy.PluginValidationError as exc:  # pragma: no cover - defensive
            raise PluginRegistrationError(str(exc)) from exc


def iter_export_contributions(
    manager: pluggy.PluginManager,
) -> Iterator[ExportContribution]:
    """Yield export format contributions from all registered plugins."""

    for contributions in manager.hook.export_formats():
        if not contributions:
            continue
        yield from _ensure_iterable(contributions)


def run_bootstrap_hooks(
    manager: pluggy.PluginManager,
    context: BootstrapContext,
) -> list[Exception]:
    """Execute bootstrap hooks, collecting exceptions per plugin."""

    errors: list[Exception] = []
    hook_caller = manager.hook.bootstrap
    for hook_impl in hook_caller.get_hookimpls():
        try:
            hook_impl.function(context=context)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)
    return errors


def load_plugin_entry_points(
    manager: pluggy.PluginManager,
    *,
    group: str = ENTRY_POINT_GROUP,
) -> list[PluginLoadError]:
    """Load plugin entry points and register them, returning any failures."""

    errors: list[PluginLoadError] = []
    for entry_point in _iter_entry_points(group):
        try:
            plugin_obj = entry_point.load()
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(PluginLoadError(entry_point.name, entry_point.value, exc))
            continue

        try:
            manager.register(plugin_obj, name=entry_point.name)
        except pluggy.PluginValidationError as exc:  # pragma: no cover - defensive
            errors.append(PluginLoadError(entry_point.name, entry_point.value, exc))
    return errors


def get_load_errors(manager: pluggy.PluginManager) -> Sequence[PluginLoadError]:
    """Return any plugin load errors captured during manager creation."""

    stored = getattr(manager, "_terminotes_load_errors", ())
    return tuple(stored)


def _ensure_iterable(contributions: Iterable[object]) -> Iterable[object]:
    """Ensure hooks may return any iterable (lists, tuples, generators)."""

    if isinstance(contributions, Iterable):
        return contributions
    raise PluginRegistrationError(
        "Plugin hook did not return an iterable contribution collection."
    )


def _iter_entry_points(group: str) -> Sequence[metadata.EntryPoint]:
    try:  # Python 3.12+
        return list(metadata.entry_points(group=group))
    except TypeError:  # pragma: no cover - fallback for older API
        entries = metadata.entry_points().get(group, ())
        return list(entries)


__all__ = [
    "PluginLoadError",
    "PluginRegistrationError",
    "create_plugin_manager",
    "get_load_errors",
    "iter_export_contributions",
    "load_plugin_entry_points",
    "register_modules",
    "run_bootstrap_hooks",
]
