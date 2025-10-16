"""Shared helpers for Terminotes CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from ..app import AppContext, bootstrap
from ..config import ConfigError, MissingConfigError
from ..git_sync import GitSyncError
from ..storage import StorageError

CONTEXT_SETTINGS: dict[str, Any] = {"help_option_names": ["-h", "--help"]}


class TerminotesCliError(click.ClickException):
    """Shared Click exception wrapper for CLI failures."""


def get_app(ctx: click.Context) -> AppContext:
    """Return a cached AppContext for the current CLI invocation."""

    app: AppContext | None = ctx.obj.get("app")
    if app is not None:
        return app

    config_path_opt: Path | None = ctx.obj.get("config_path")

    try:
        app = bootstrap(config_path_opt, missing_hint=True)
    except MissingConfigError as exc:
        raise TerminotesCliError(
            "Configuration not found. Run 'tn config' once to set up Terminotes."
        ) from exc
    except (ConfigError, GitSyncError, StorageError) as exc:  # pragma: no cover
        raise TerminotesCliError(str(exc)) from exc

    ctx.obj["app"] = app
    return app
