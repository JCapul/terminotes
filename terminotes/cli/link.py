"""Link command for Terminotes CLI."""

from __future__ import annotations

import click

from ..git_sync import GitSyncError
from ..services.notes import create_link_entry
from ..storage import StorageError
from ..utils.datetime_fmt import parse_user_datetime
from ._common import TerminotesCliError, get_app


@click.command(name="link")
@click.argument("url")
@click.argument("comment", nargs=-1)
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Tag to associate with the link note (repeatable)",
)
@click.option(
    "-c",
    "--created",
    "created_opt",
    type=str,
    default=None,
    help="Set creation time (ISO 8601 or 'YYYY-MM-DD HH:MM').",
)
@click.pass_context
def link(
    ctx: click.Context,
    url: str,
    comment: tuple[str, ...],
    tags: tuple[str, ...],
    created_opt: str | None,
) -> None:
    """Capture a URL with optional comment and Wayback fallback."""

    app = get_app(ctx)
    comment_text = " ".join(comment).strip()

    created_at = None
    if created_opt:
        try:
            created_at = parse_user_datetime(created_opt)
        except ValueError as exc:
            raise TerminotesCliError(str(exc)) from exc

    try:
        note, snapshot = create_link_entry(
            app,
            url,
            comment_text,
            tags=tags,
            created_at=created_at,
            warn=lambda msg: click.echo(msg),
        )
    except ValueError as exc:
        raise TerminotesCliError(str(exc)) from exc
    except (StorageError, GitSyncError) as exc:
        raise TerminotesCliError(str(exc)) from exc

    if snapshot is not None:
        click.echo(f"Saved link note {note.id} (Wayback fallback: {snapshot['url']})")
    else:
        click.echo(f"Saved link note {note.id}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(link)
