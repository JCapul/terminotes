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


class TerminotesPluginManager:
    """Wrapper around pluggy's ``PluginManager`` with Terminotes defaults."""

    def __init__(self, *, load_entry_points: bool = True) -> None:
        self._manager = pluggy.PluginManager(PLUGIN_NAMESPACE)
        self._manager.add_hookspecs(TerminotesHookSpec)
        if load_entry_points:
            self.load_entry_points()

    @property
    def manager(self) -> pluggy.PluginManager:
        return self._manager

    def register_modules(self, modules: Sequence[object]) -> None:
        for module in modules:
            try:
                self._manager.register(module)
            except pluggy.PluginValidationError as exc:  # pragma: no cover - defensive
                raise PluginRegistrationError(str(exc)) from exc

    def load_entry_points(self, group: str = ENTRY_POINT_GROUP) -> None:
        self._manager.load_setuptools_entrypoints(group)

    def iter_export_contributions(self) -> Iterator[ExportContribution]:
        for contributions in self._manager.hook.export_formats():
            if not contributions:
                continue
            yield from _ensure_iterable(contributions)

    def run_bootstrap(self, context: BootstrapContext) -> None:
        self._manager.hook.bootstrap(context=context)


@lru_cache(maxsize=1)
def _builtin_plugin_modules() -> Tuple[object, ...]:
    from . import html, markdown

    return (html, markdown)


@lru_cache(maxsize=1)
def _shared_plugin_manager() -> TerminotesPluginManager:
    manager = TerminotesPluginManager()
    manager.register_modules(_builtin_plugin_modules())
    return manager


def get_plugin_manager() -> TerminotesPluginManager:
    return _shared_plugin_manager()


def reset_plugin_manager_cache() -> None:
    _shared_plugin_manager.cache_clear()


def load_export_contributions() -> dict[str, ExportContribution]:
    manager = get_plugin_manager()
    contributions: dict[str, ExportContribution] = {}
    for contribution in manager.iter_export_contributions():
        key = contribution.format_id.lower()
        if key in contributions:
            raise PluginRegistrationError(
                f"Duplicate export format detected: '{contribution.format_id}'."
            )
        contributions[key] = contribution
    return contributions


def run_bootstrap(context: BootstrapContext) -> None:
    manager = get_plugin_manager()
    return manager.run_bootstrap(context)


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
    "TerminotesPluginManager",
    "get_plugin_manager",
    "load_export_contributions",
    "reset_plugin_manager_cache",
    "run_bootstrap",
]
