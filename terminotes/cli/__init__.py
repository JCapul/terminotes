"""Terminotes CLI package."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import click

from . import (
    config_cmd,
    delete,
    edit,
    export_cmd,
    info,
    link,
    log,
    ls,
    prune,
    search,
    sync,
)
from ._common import CONTEXT_SETTINGS, TerminotesCliError

__all__ = ["cli", "main", "TerminotesCliError"]


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--config",
    "config_path_opt",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to configuration TOML file.",
)
@click.pass_context
def cli(ctx: click.Context, config_path_opt: Path | None) -> None:
    """Terminotes command group."""

    ctx.ensure_object(dict)
    invoked = ctx.invoked_subcommand

    if invoked is None:
        click.echo(ctx.command.get_help(ctx))
        ctx.exit(0)

    ctx.obj["config_path"] = config_path_opt


for register_command in (
    edit.register,
    log.register,
    link.register,
    delete.register,
    prune.register,
    sync.register,
    config_cmd.register,
    ls.register,
    search.register,
    export_cmd.register,
    info.register,
):
    register_command(cli)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv) if argv is not None else None
    try:
        return cli.main(args=args, prog_name="tn", standalone_mode=False)
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        return 1
    except SystemExit as exc:
        return int(exc.code)
