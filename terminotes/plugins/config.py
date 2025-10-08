"""Configuration helpers for Terminotes plugins."""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ..config import TerminotesConfig
from .types import PluginSettingsGetter

_PLUGINS_TABLE = "plugins"
_EMPTY_MAPPING: Mapping[str, Any] = MappingProxyType({})


def build_settings_getter(config: TerminotesConfig) -> PluginSettingsGetter:
    """Return a callable that fetches plugin-specific configuration blocks."""

    cache: Mapping[str, Mapping[str, Any]] | None = None

    def get_settings(
        plugin_id: str,
        *,
        default: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        nonlocal cache
        if cache is None:
            cache = _load_plugins_table(config.source_path)
        data = cache.get(plugin_id)
        if data is not None:
            return data
        if default is not None:
            return MappingProxyType(dict(default))
        return _EMPTY_MAPPING

    return get_settings


def _load_plugins_table(
    source_path: Path | None,
) -> Mapping[str, Mapping[str, Any]]:
    if source_path is None or not source_path.exists():
        return {}

    try:
        with source_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except OSError:  # pragma: no cover - defensive for IO errors
        return {}

    plugins_table = raw.get(_PLUGINS_TABLE)
    if not isinstance(plugins_table, dict):
        return {}

    normalized: dict[str, Mapping[str, Any]] = {}
    for key, value in plugins_table.items():
        if not isinstance(key, str):  # pragma: no cover - ignore invalid keys
            continue
        if isinstance(value, dict):
            normalized[key] = MappingProxyType(dict(value))
        else:
            normalized[key] = _EMPTY_MAPPING
    return normalized


__all__ = ["build_settings_getter"]
