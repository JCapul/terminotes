"""Delete-related workflows for the CLI."""

from __future__ import annotations

from ..app import AppContext


def delete_note(ctx: AppContext, note_id: int) -> None:
    """Remove a note and commit the database change locally."""

    ctx.storage.delete_note(note_id)
    ctx.git_sync.commit_db_update(ctx.storage.path, f"chore(db): delete note {note_id}")
