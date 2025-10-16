"""Config command for Terminotes CLI."""

from __future__ import annotations

from pathlib import Path

import click

from ..config import DEFAULT_CONFIG_PATH, bootstrap_config_file
from ._common import TerminotesCliError


@click.command(name="config")
@click.pass_context
def config(ctx: click.Context) -> None:
    """Open the Terminotes configuration file in the editor."""

    selected_path: Path | None = ctx.obj.get("config_path")
    effective_path = selected_path or DEFAULT_CONFIG_PATH

    created = bootstrap_config_file(effective_path)
    config_path = effective_path

    try:
        result = click.edit(filename=str(config_path))
    except OSError as exc:  # pragma: no cover - editor launch failure rare
        raise TerminotesCliError(f"Failed to launch editor: {exc}") from exc

    if created:
        click.echo(f"Created configuration at {config_path}")

    if result is None:
        click.echo(f"Opened configuration at {config_path}")
    else:  # pragma: no cover - depends on click behaviour
        click.echo(f"Updated configuration at {config_path}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(config)
