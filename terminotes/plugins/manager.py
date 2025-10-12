"""Helpers for creating and working with the Terminotes plugin manager."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from functools import lru_cache
from typing import Iterable as TypingIterable
from typing import Tuple

import pluggy

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE
from .spec import TerminotesHookSpec
from .types import BootstrapContext, ExportContribution


class PluginRegistrationError(RuntimeError):
    """Raised when a plugin fails validation or registration."""


def create_plugin_manager(*, load_entry_points: bool = True) -> pluggy.PluginManager:
    """Instantiate a pluggy ``PluginManager`` configured for Terminotes."""

    manager = pluggy.PluginManager(PLUGIN_NAMESPACE)
    manager.add_hookspecs(TerminotesHookSpec)

    if load_entry_points:
        load_plugin_entry_points(manager)

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

    hook_caller = manager.hook.bootstrap
    hook_impls = list(hook_caller.get_hookimpls())
    if not hook_impls:
        return []

    plugins_in_order = [impl.plugin for impl in hook_impls]
    errors: list[Exception] = []

    for plugin in plugins_in_order:
        others = [p for p in plugins_in_order if p is not plugin]
        subset = manager.subset_hook_caller("bootstrap", others)
        try:
            subset(context=context)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    return errors


def load_plugin_entry_points(
    manager: pluggy.PluginManager,
    *,
    group: str = ENTRY_POINT_GROUP,
) -> None:
    """Load plugin entry points via ``importlib.metadata`` integration."""

    manager.load_setuptools_entrypoints(group)


def iter_plugin_modules() -> Tuple[object, ...]:
    """Return plugin modules bundled with Terminotes."""

    return _builtin_plugin_modules()


@lru_cache(maxsize=1)
def _builtin_plugin_modules() -> Tuple[object, ...]:
    from . import html, markdown

    return (html, markdown)


@lru_cache(maxsize=1)
def _build_plugin_manager() -> pluggy.PluginManager:
    manager = create_plugin_manager()
    register_modules(manager, iter_plugin_modules())
    return manager


def get_plugin_manager() -> pluggy.PluginManager:
    """Return the cached plugin manager instance."""

    return _build_plugin_manager()


def reset_plugin_manager_cache() -> None:
    """Clear cached plugin manager so future calls rebuild state."""

    _build_plugin_manager.cache_clear()
    _builtin_plugin_modules.cache_clear()


def load_export_contributions() -> dict[str, ExportContribution]:
    """Collect exporter contributions from all registered plugins."""

    manager = get_plugin_manager()

    contributions: dict[str, ExportContribution] = {}
    for contribution in iter_export_contributions(manager):
        key = contribution.format_id.lower()
        if key in contributions:
            raise PluginRegistrationError(
                f"Duplicate export format detected: '{contribution.format_id}'."
            )
        contributions[key] = contribution

    return contributions


def run_bootstrap(context: BootstrapContext) -> list[Exception]:
    """Execute bootstrap hooks using the shared plugin manager."""

    manager = get_plugin_manager()
    return run_bootstrap_hooks(manager, context)


def _ensure_iterable(
    contributions: object,
) -> TypingIterable[ExportContribution]:
    """Normalize hook return values to a concrete iterable of contributions."""

    if isinstance(contributions, ExportContribution):
        return (contributions,)

    if not isinstance(contributions, Iterable) or isinstance(
        contributions, (str, bytes)
    ):
        raise PluginRegistrationError(
            "Plugin hook did not return an iterable contribution collection."
        )

    normalized: list[ExportContribution] = []
    for item in contributions:
        if not isinstance(item, ExportContribution):
            raise PluginRegistrationError(
                "Export contributions must be ExportContribution instances."
            )
        normalized.append(item)
    return tuple(normalized)


__all__ = [
    "PluginRegistrationError",
    "create_plugin_manager",
    "get_plugin_manager",
    "iter_export_contributions",
    "iter_plugin_modules",
    "load_export_contributions",
    "load_plugin_entry_points",
    "register_modules",
    "reset_plugin_manager_cache",
    "run_bootstrap",
    "run_bootstrap_hooks",
]
