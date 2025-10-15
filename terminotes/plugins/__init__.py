"""Terminotes plugin infrastructure based on pluggy."""

from __future__ import annotations

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE, hookimpl, hookspec
from .manager import (
    PluginRegistrationError,
    TerminotesPluginManager,
    get_plugin_manager,
    load_export_contributions,
    reset_plugin_manager_cache,
    run_bootstrap,
)
from .types import ExportContribution

__all__ = [
    "ExportContribution",
    "ENTRY_POINT_GROUP",
    "PLUGIN_NAMESPACE",
    "PluginRegistrationError",
    "TerminotesPluginManager",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "load_export_contributions",
    "reset_plugin_manager_cache",
    "run_bootstrap",
]
