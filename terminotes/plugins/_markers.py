"""Pluggy markers and constants for Terminotes plugin namespace."""

from __future__ import annotations

import pluggy

PLUGIN_NAMESPACE = "terminotes"
ENTRY_POINT_GROUP = "terminotes.plugins"

hookspec = pluggy.HookspecMarker(PLUGIN_NAMESPACE)
hookimpl = pluggy.HookimplMarker(PLUGIN_NAMESPACE)

__all__ = ["PLUGIN_NAMESPACE", "ENTRY_POINT_GROUP", "hookspec", "hookimpl"]
