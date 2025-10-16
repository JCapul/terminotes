"""Delete command for Terminotes CLI."""

from __future__ import annotations

import click

from ..git_sync import GitSyncError
from ..services.delete import delete_note as delete_note_workflow
from ..storage import StorageError
from ._common import TerminotesCliError, get_app


@click.command(name="delete")
@click.option(
    "-y",
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.argument("note_id", type=int)
@click.pass_context
def delete(ctx: click.Context, note_id: int, assume_yes: bool) -> None:
    """Delete a note identified by NOTE_ID from the database."""

    app = get_app(ctx)
    if not assume_yes:
        confirm = click.confirm(
            f"Delete note {note_id}?", default=False, show_default=True
        )
        if not confirm:
            raise TerminotesCliError("Deletion aborted.")

    try:
        delete_note_workflow(app, note_id)
    except StorageError as exc:
        raise TerminotesCliError(str(exc)) from exc
    except GitSyncError as exc:  # pragma: no cover - pass-through
        raise TerminotesCliError(str(exc)) from exc

    click.echo(f"Deleted note {note_id}")


def register(cli: click.Group) -> None:
    """Register the command with the root CLI group."""

    cli.add_command(delete)
