"""Log command for Terminotes CLI."""

from __future__ import annotations

import click

from ..git_sync import GitSyncError
from ..services.notes import create_log_entry
from ..storage import StorageError
from ..utils.datetime_fmt import parse_user_datetime
from ._common import TerminotesCliError, get_app


@click.command(name="log")
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Tag to associate with the new note (repeatable)",
)
@click.option(
    "-c",
    "--created",
    "created_opt",
    type=str,
    default=None,
    help="Set creation time (ISO 8601 or 'YYYY-MM-DD HH:MM').",
)
@click.argument("content", nargs=-1)
@click.pass_context
def log(
    ctx: click.Context,
    content: tuple[str, ...],
    tags: tuple[str, ...],
    created_opt: str | None,
) -> None:
    """Create a new log entry from CLI content."""

    app = get_app(ctx)

    body = " ".join(content).strip()
    if not body:
        raise TerminotesCliError("Content is required for 'tn log'.")

    tags = ("log",) + tags

    created_at = None
    if created_opt:
        try:
            created_at = parse_user_datetime(created_opt)
        except ValueError as exc:
            raise TerminotesCliError(str(exc)) from exc

    try:
        note = create_log_entry(app, body, tags=tags, created_at=created_at)
    except (StorageError, GitSyncError) as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note.id} (tagged as log)")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(log)
