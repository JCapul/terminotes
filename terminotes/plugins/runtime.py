"""Runtime helpers for managing Terminotes plugin manager instances."""

from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import pluggy

from . import (
    PluginLoadError,
    PluginRegistrationError,
    create_plugin_manager,
    get_load_errors,
    iter_export_contributions,
    register_modules,
    run_bootstrap_hooks,
)
from .builtin import BUILTIN_PLUGINS
from .types import BootstrapContext, ExportContribution

ContributionResult = Tuple[dict[str, ExportContribution], Tuple[PluginLoadError, ...]]


def iter_plugin_modules() -> Tuple[object, ...]:
    """Return plugin modules bundled with Terminotes."""

    return BUILTIN_PLUGINS


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


def load_export_contributions() -> ContributionResult:
    """Collect exporter contributions and associated load errors."""

    manager = get_plugin_manager()

    contributions: dict[str, ExportContribution] = {}
    for contribution in iter_export_contributions(manager):
        key = contribution.format_id.lower()
        if key in contributions:
            raise PluginRegistrationError(
                f"Duplicate export format detected: '{contribution.format_id}'."
            )
        contributions[key] = contribution

    return contributions, tuple(get_load_errors(manager))


def run_bootstrap(context: BootstrapContext) -> list[Exception]:
    """Execute bootstrap hooks using the shared plugin manager."""

    manager = get_plugin_manager()
    return run_bootstrap_hooks(manager, context)
