"""List command for Terminotes CLI."""

from __future__ import annotations

import click

from ..storage import Storage, StorageError
from ..utils.datetime_fmt import to_user_friendly_local
from ._common import TerminotesCliError, get_app


@click.command(name="ls")
@click.option("-n", "--limit", type=int, default=10, help="Maximum notes to list")
@click.option(
    "-r",
    "--reverse",
    is_flag=True,
    help="Reverse order (oldest first for current sort)",
)
@click.option(
    "-t",
    "--tag",
    "tags",
    multiple=True,
    help="Filter notes by tag (repeatable)",
)
@click.pass_context
def ls(ctx: click.Context, limit: int, reverse: bool, tags: tuple[str, ...]) -> None:
    """List the most recent notes (by last edit time)."""

    app = get_app(ctx)
    storage: Storage = app.storage

    try:
        notes = list(storage.list_notes(limit=limit, tags=tags))
    except StorageError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    if reverse:
        notes = list(reversed(notes))

    for note in notes:
        updated = to_user_friendly_local(note.updated_at)
        title = note.title or ""
        tag_list = sorted(tag.name for tag in note.tags)
        tag_suffix = f"  [tags: {', '.join(tag_list)}]" if tag_list else ""
        click.echo(f"{note.id:>4}  {updated}  {title}{tag_suffix}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(ls)
