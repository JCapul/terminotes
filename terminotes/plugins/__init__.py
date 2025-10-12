"""Terminotes plugin infrastructure based on pluggy."""

from __future__ import annotations

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE, hookimpl, hookspec
from .config import build_settings_getter
from .manager import (
    PluginRegistrationError,
    TerminotesPluginManager,
    get_plugin_manager,
    load_export_contributions,
    reset_plugin_manager_cache,
    run_bootstrap,
)
from .types import BootstrapContext, ExportContribution, PluginSettingsGetter

__all__ = [
    "BootstrapContext",
    "ExportContribution",
    "ENTRY_POINT_GROUP",
    "PLUGIN_NAMESPACE",
    "PluginRegistrationError",
    "PluginSettingsGetter",
    "TerminotesPluginManager",
    "build_settings_getter",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "load_export_contributions",
    "reset_plugin_manager_cache",
    "run_bootstrap",
]
