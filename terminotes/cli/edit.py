"""Edit command for Terminotes CLI."""

from __future__ import annotations

import click

from ..editor import EditorError, open_editor
from ..git_sync import GitSyncError
from ..services.notes import create_via_editor, update_via_editor
from ..storage import StorageError
from ._common import TerminotesCliError, get_app


@click.command(name="edit")
@click.option(
    "-i",
    "--id",
    "note_id",
    type=int,
    default=None,
    help=("Edit the note with this id. When omitted, a new note is created."),
)
@click.option(
    "-l",
    "--last",
    "edit_last",
    is_flag=True,
    help="Edit the last updated note (mutually exclusive with --id)",
)
@click.pass_context
def edit(ctx: click.Context, note_id: int | None, edit_last: bool) -> None:
    """Create a new note or edit an existing one."""

    app = get_app(ctx)

    if note_id is not None and edit_last:
        raise TerminotesCliError("Use only one of --id or --last.")

    if note_id or edit_last:
        note_id = -1 if edit_last else note_id

        try:
            updated = update_via_editor(
                app,
                note_id,
                edit_fn=open_editor,
                warn=lambda msg: click.echo(msg),
            )
        except (EditorError, StorageError, GitSyncError) as exc:
            raise TerminotesCliError(str(exc)) from exc

        click.echo(f"Updated note {updated.id}")
        return

    try:
        note_obj = create_via_editor(
            app,
            edit_fn=open_editor,
            warn=lambda msg: click.echo(msg),
        )
    except (EditorError, StorageError, GitSyncError) as exc:
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Created note {note_obj.id}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(edit)
