"""Terminotes plugin infrastructure based on pluggy."""

from __future__ import annotations

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE, hookimpl, hookspec
from .config import build_settings_getter
from .manager import (
    PluginRegistrationError,
    create_plugin_manager,
    get_plugin_manager,
    iter_export_contributions,
    iter_plugin_modules,
    load_export_contributions,
    load_plugin_entry_points,
    register_modules,
    reset_plugin_manager_cache,
    run_bootstrap,
    run_bootstrap_hooks,
)
from .types import BootstrapContext, ExportContribution, PluginSettingsGetter

__all__ = [
    "BootstrapContext",
    "ExportContribution",
    "ENTRY_POINT_GROUP",
    "PLUGIN_NAMESPACE",
    "PluginRegistrationError",
    "PluginSettingsGetter",
    "build_settings_getter",
    "create_plugin_manager",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "iter_export_contributions",
    "iter_plugin_modules",
    "load_export_contributions",
    "load_plugin_entry_points",
    "register_modules",
    "reset_plugin_manager_cache",
    "run_bootstrap",
    "run_bootstrap_hooks",
]
