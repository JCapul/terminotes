"""Export command for Terminotes CLI."""

from __future__ import annotations

from pathlib import Path

import click

from ..services.export import (
    ExportError,
    get_export_format_descriptions,
)
from ..services.export import (
    export_notes as run_export,
)
from ._common import TerminotesCliError, get_app


@click.command(name="export")
@click.option(
    "-l",
    "--list-formats",
    "list_formats",
    is_flag=True,
    help="List available export formats and exit.",
)
@click.option(
    "-f",
    "--format",
    "export_format",
    type=str,
    required=False,
    metavar="FORMAT",
    help="Export format identifier.",
)
@click.option(
    "-d",
    "--dest",
    "destination",
    type=click.Path(path_type=Path, file_okay=False),
    required=False,
    help="Destination directory for the export",
)
@click.pass_context
def export(
    ctx: click.Context,
    list_formats: bool,
    export_format: str | None,
    destination: Path | None,
) -> None:
    """Export notes for the configured repository."""

    app = get_app(ctx)

    if list_formats:
        try:
            descriptions = get_export_format_descriptions(app.config)
        except ExportError as exc:
            raise TerminotesCliError(str(exc)) from exc

        if not descriptions:
            click.echo("No export formats are available.")
        else:
            click.echo("Available export formats:\n")
            for fmt, desc in descriptions:
                if desc:
                    click.echo(f"  - {fmt}: {desc}")
                else:
                    click.echo(f"  - {fmt}")
        ctx.exit(0)

    if export_format is None:
        raise TerminotesCliError("Missing option '--format'.")

    if destination is None:
        raise TerminotesCliError("Missing option '--dest'.")

    if destination.exists() and destination.is_file():
        raise TerminotesCliError("Destination must be a directory path.")

    try:
        count = run_export(
            app.config,
            app.storage,
            export_format=export_format,
            destination=destination,
        )
    except ExportError as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Exported {count} notes to {destination}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(export)
