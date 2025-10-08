"""Terminotes plugin infrastructure based on pluggy."""

from __future__ import annotations

from ._markers import ENTRY_POINT_GROUP, PLUGIN_NAMESPACE, hookimpl, hookspec
from .config import build_settings_getter
from .manager import (
    PluginLoadError,
    PluginRegistrationError,
    create_plugin_manager,
    get_load_errors,
    iter_export_contributions,
    load_plugin_entry_points,
    register_modules,
    run_bootstrap_hooks,
)
from .types import BootstrapContext, ExportContribution, PluginSettingsGetter

__all__ = [
    "BootstrapContext",
    "ExportContribution",
    "ENTRY_POINT_GROUP",
    "PLUGIN_NAMESPACE",
    "PluginLoadError",
    "PluginRegistrationError",
    "PluginSettingsGetter",
    "build_settings_getter",
    "create_plugin_manager",
    "get_load_errors",
    "hookimpl",
    "hookspec",
    "iter_export_contributions",
    "load_plugin_entry_points",
    "register_modules",
    "run_bootstrap_hooks",
]
