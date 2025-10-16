"""Search command for Terminotes CLI."""

from __future__ import annotations

import click

from ..storage import Storage, StorageError
from ..utils.datetime_fmt import to_user_friendly_local
from ._common import TerminotesCliError, get_app


@click.command(name="search")
@click.argument("pattern")
@click.option("-n", "--limit", type=int, default=20, help="Maximum matches to show")
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
    help="Filter matches by tag (repeatable)",
)
@click.pass_context
def search(
    ctx: click.Context,
    pattern: str,
    limit: int,
    reverse: bool,
    tags: tuple[str, ...],
) -> None:
    """Search notes for a pattern (case-insensitive substring)."""

    app = get_app(ctx)
    storage: Storage = app.storage

    pat = (pattern or "").strip()
    if not pat:
        raise TerminotesCliError("Search pattern must not be empty.")

    try:
        matches = list(storage.search_notes(pat, tags=tags))
    except StorageError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    if reverse:
        matches = list(reversed(matches))

    if limit > 0:
        matches = matches[:limit]
    else:
        matches = []

    for note in matches:
        updated = to_user_friendly_local(note.updated_at)
        title = note.title or ""
        tag_list = sorted(tag.name for tag in note.tags)
        tag_suffix = f"  [tags: {', '.join(tag_list)}]" if tag_list else ""
        click.echo(f"{note.id:>4}  {updated}  {title}{tag_suffix}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(search)
